from sqlmodel import desc, select
import difflib

from app.core.database import SessionDep
from app.models.palette import Palette, Palette_Change, Palette_Color, Palette_Snapshot
from app.schemas.palette import PaletteCreate, PaletteSnapshotSave
from app.utils.lexicographic_ranker import LexicographicRanker


class PaletteService:
    # Creates a new palette along with its initial snapshot and starting colors.
    def create_palette(paletteSchema: PaletteCreate, user_id: int, session: SessionDep):
        new_palette = Palette(
            user_id=user_id,
            title=paletteSchema.title,
            description=paletteSchema.description,
        )
        session.add(new_palette)
        session.flush()

        new_snapshot = Palette_Snapshot(
            palette_id=new_palette.id, comment="Initial palette creation"
        )
        session.add(new_snapshot)
        session.flush()

        keys = LexicographicRanker.initial_keys(len(paletteSchema.palette_colors))
        for i, color_schema in enumerate(paletteSchema.palette_colors):
            new_color = Palette_Color(
                palette_snapshot_id=new_snapshot.id,
                hex=color_schema.hex,
                label=color_schema.label,
                position_key=keys[i],
            )
            session.add(new_color)

        session.commit()
        session.refresh(new_palette)
        return new_palette

    # Retrieves a palette by its ID.
    def get_palette(palette_id: int, session: SessionDep):
        query = select(Palette).where(Palette.id == palette_id)
        return session.exec(query).first()

    # Reconstructs the active color list for a specific snapshot by resolving past changes.
    def get_snapshot_state(
        snapshot: Palette_Snapshot, session: SessionDep
    ) -> list[Palette_Color]:
        current_snapshot = snapshot
        active_colors: dict[int, Palette_Color] = {}
        deleted_color_ids: set[int] = set()

        while current_snapshot:
            changes = session.exec(
                select(Palette_Change).where(
                    Palette_Change.new_snapshot_id == current_snapshot.id
                )
            ).all()
            for change in changes:
                if change.new_color_id is None and change.previous_color_id is not None:
                    deleted_color_ids.add(change.previous_color_id)
                elif change.new_color_id is not None:
                    if (
                        change.new_color_id not in deleted_color_ids
                        and change.new_color_id not in active_colors
                    ):
                        color = session.exec(
                            select(Palette_Color).where(
                                Palette_Color.id == change.new_color_id
                            )
                        ).first()
                        if color:
                            active_colors[color.id] = color
                    if change.previous_color_id is not None:
                        deleted_color_ids.add(change.previous_color_id)

            base_colors = session.exec(
                select(Palette_Color).where(
                    Palette_Color.palette_snapshot_id == current_snapshot.id
                )
            ).all()
            for color in base_colors:
                if color.id not in deleted_color_ids and color.id not in active_colors:
                    active_colors[color.id] = color

            if current_snapshot.parent_snapshot_id:
                current_snapshot = session.exec(
                    select(Palette_Snapshot).where(
                        Palette_Snapshot.id == current_snapshot.parent_snapshot_id
                    )
                ).first()
            else:
                break

        return sorted(active_colors.values(), key=lambda c: c.position_key)

    # Retrieves the most recent snapshot for a palette and its active colors.
    def get_latest_palette_snapshot(
        palette_id: int, session: SessionDep
    ) -> tuple[Palette_Snapshot | None, list[Palette_Color]]:
        query = (
            select(Palette_Snapshot)
            .where(Palette_Snapshot.palette_id == palette_id)
            .order_by(desc(Palette_Snapshot.id))
        )
        latest_snapshot = session.exec(query).first()

        if not latest_snapshot:
            return None, []

        return latest_snapshot, PaletteService.get_snapshot_state(
            latest_snapshot, session
        )

    # Calculates the number of added, deleted, and modified colors for a given snapshot.
    def get_diff_counts(snap_id: int, session: SessionDep):
        changes = session.exec(
            select(Palette_Change).where(Palette_Change.new_snapshot_id == snap_id)
        ).all()
        added, deleted, modified = 0, 0, 0
        for c in changes:
            if c.previous_color_id and c.new_color_id:
                modified += 1
            elif c.new_color_id:
                added += 1
            elif c.previous_color_id:
                deleted += 1
        return added, deleted, modified

    # Builds a graph of a palette's history, grouping snapshots into the main branch and divergent branches.
    def get_palette_history(palette_id: int, session: SessionDep):
        query = (
            select(Palette_Snapshot)
            .where(Palette_Snapshot.palette_id == palette_id)
            .order_by(desc(Palette_Snapshot.created_at))
        )

        snapshots = session.exec(query).all()
        if not snapshots:
            return {"main": [], "branches": {}}

        all_commits = {}
        for snap in snapshots:
            colors = PaletteService.get_snapshot_state(snap, session)
            added, deleted, modified = PaletteService.get_diff_counts(snap.id, session)

            all_commits[snap.id] = {
                "id": snap.id,
                "palette_id": snap.palette_id,
                "parent_snapshot_id": snap.parent_snapshot_id,
                "comment": snap.comment,
                "created_at": snap.created_at,
                "palette_colors": [{"hex": c.hex, "label": c.label} for c in colors],
                "colors_added": added,
                "colors_deleted": deleted,
                "colors_modified": modified,
                "children": [],
            }

        for cid, commit in all_commits.items():
            pid = commit["parent_snapshot_id"]
            if pid and pid in all_commits:
                all_commits[pid]["children"].append(cid)

        terminal_nodes = [cid for cid, c in all_commits.items() if not c["children"]]
        terminal_nodes.sort(
            key=lambda nid: all_commits[nid]["created_at"], reverse=True
        )

        main_tip_id = terminal_nodes[0] if terminal_nodes else snapshots[0].id

        main_branch = []
        curr_id = main_tip_id
        while curr_id:
            main_branch.append(all_commits[curr_id])
            curr_id = all_commits[curr_id]["parent_snapshot_id"]

        main_branch_set = {c["id"] for c in main_branch}

        branches = {}
        branch_counter = 1

        for term_id in terminal_nodes:
            if term_id == main_tip_id:
                continue

            branch_path = []
            curr_id = term_id
            while curr_id and curr_id not in main_branch_set:
                branch_path.append(all_commits[curr_id])
                curr_id = all_commits[curr_id]["parent_snapshot_id"]

            if branch_path:
                branches[f"branch_{branch_counter}"] = branch_path
                branch_counter += 1

        return {"main": main_branch, "branches": branches}

    # Creates a new snapshot with calculated differences compared to its parent snapshot.
    def save_palette(
        palette_id: int,
        saveSchema: PaletteSnapshotSave,
        user_id: int,
        session: SessionDep,
    ):
        palette = PaletteService.get_palette(palette_id, session)
        if not palette:
            raise ValueError("Palette not found.")
        if palette.user_id != user_id:
            raise PermissionError("You do not have permission to modify this palette.")

        if saveSchema.parent_snapshot_id:
            prev_snapshot = session.exec(
                select(Palette_Snapshot).where(
                    Palette_Snapshot.id == saveSchema.parent_snapshot_id,
                    Palette_Snapshot.palette_id == palette_id,
                )
            ).first()
            if not prev_snapshot:
                raise ValueError("Parent snapshot not found for this palette.")
            prev_colors = PaletteService.get_snapshot_state(prev_snapshot, session)
        else:
            prev_snapshot, prev_colors = PaletteService.get_latest_palette_snapshot(
                palette_id, session
            )
            if not prev_snapshot:
                raise ValueError("Palette has no previous snapshot to save upon.")

        new_inputs = saveSchema.palette_colors

        def _get_identity(c):
            return f"{c.hex}_{c.label}"

        old_ids = [_get_identity(c) for c in prev_colors]
        new_ids = [_get_identity(c) for c in new_inputs]

        matcher = difflib.SequenceMatcher(None, old_ids, new_ids)
        opcodes = matcher.get_opcodes()

        if (
            len(opcodes) == 1
            and opcodes[0][0] == "equal"
            and opcodes[0][2] - opcodes[0][1] == len(prev_colors)
        ):
            raise ValueError("No changes detected in palette colors.")

        new_snapshot = Palette_Snapshot(
            palette_id=palette_id,
            parent_snapshot_id=prev_snapshot.id,
            comment=saveSchema.comment,
        )
        session.add(new_snapshot)
        session.flush()

        new_colors_final = [None] * len(new_inputs)
        changes_to_record = []
        replacements_map = {}

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "equal":
                for old_idx, new_idx in zip(range(i1, i2), range(j1, j2)):
                    new_colors_final[new_idx] = prev_colors[old_idx]

            elif tag == "delete":
                for old_idx in range(i1, i2):
                    changes_to_record.append(
                        Palette_Change(
                            previous_snapshot_id=prev_snapshot.id,
                            new_snapshot_id=new_snapshot.id,
                            previous_color_id=prev_colors[old_idx].id,
                            new_color_id=None,
                        )
                    )

            elif tag == "replace":
                old_indices = list(range(i1, i2))
                new_indices = list(range(j1, j2))

                for k in range(max(len(old_indices), len(new_indices))):
                    if k < len(old_indices) and k < len(new_indices):
                        replacements_map[new_indices[k]] = prev_colors[
                            old_indices[k]
                        ].id

                    elif k < len(old_indices):
                        changes_to_record.append(
                            Palette_Change(
                                previous_snapshot_id=prev_snapshot.id,
                                new_snapshot_id=new_snapshot.id,
                                previous_color_id=prev_colors[old_indices[k]].id,
                                new_color_id=None,
                            )
                        )

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == "insert" or tag == "replace":
                for new_idx in range(j1, j2):
                    req_color = new_inputs[new_idx]

                    left_key = (
                        new_colors_final[new_idx - 1].position_key
                        if new_idx > 0 and new_colors_final[new_idx - 1]
                        else None
                    )
                    right_key = None

                    for scan_idx in range(new_idx + 1, len(new_inputs)):
                        if new_colors_final[scan_idx]:
                            right_key = new_colors_final[scan_idx].position_key
                            break

                    if left_key and not right_key:
                        pos_key = LexicographicRanker.increment(left_key[-1])
                        if len(left_key) > 1:
                            pos_key = left_key[:-1] + pos_key
                    elif not left_key and right_key:
                        pos_key = LexicographicRanker.midpoint("`", right_key)
                    else:
                        pos_key = LexicographicRanker.midpoint(
                            left_key or "`", right_key or "z"
                        )

                    new_c = Palette_Color(
                        palette_snapshot_id=new_snapshot.id,
                        hex=req_color.hex,
                        label=req_color.label,
                        position_key=pos_key,
                    )
                    session.add(new_c)
                    session.flush()
                    new_colors_final[new_idx] = new_c

                    prev_color_id = replacements_map.get(new_idx, None)

                    changes_to_record.append(
                        Palette_Change(
                            previous_snapshot_id=prev_snapshot.id,
                            new_snapshot_id=new_snapshot.id,
                            previous_color_id=prev_color_id,
                            new_color_id=new_c.id,
                        )
                    )

        for change in changes_to_record:
            session.add(change)

        session.commit()
        return new_snapshot, changes_to_record
