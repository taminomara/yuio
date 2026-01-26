import dataclasses
import pathlib

import yuio.git
import yuio.io

if __name__ == "__main__":
    repo = yuio.git.Repo(pathlib.Path(__file__).parent.parent)

    status = repo.status()

    yuio.io.heading("Repository status")

    for k, v in dataclasses.asdict(status).items():
        if k != "changes":
            yuio.io.info("%s: <c note>%s</c>", k, v)

    if not status.branch:
        yuio.io.warning("Detached head.")
    if status.cherry_pick_head:
        yuio.io.warning("Cherry pick is in progress.")
    if status.merge_head:
        yuio.io.warning("Merge is in progress.")
    if status.rebase_head:
        yuio.io.warning("Rebase is in progress.")
    if status.revert_head:
        yuio.io.warning("Revert is in progress.")
    if status.bisect_start:
        yuio.io.warning("Bisect is in progress.")

    yuio.io.heading("Changes")

    if changes := status.changes:
        for change in changes:
            if isinstance(change, yuio.git.UnmergedFileStatus):
                yuio.io.info(
                    "%s: <c note>unmerged %s%s</c>",
                    change.path,
                    change.us.value,
                    change.them.value,
                )
            elif isinstance(change, yuio.git.FileStatus):
                path = (
                    change.path
                    if change.path_from is None
                    else f"{change.path_from} -> {change.path}"
                )
                yuio.io.info(
                    "%s: <c note>%s%s</c>", path, change.staged.value, change.tree.value
                )
            else:
                yuio.io.info("%s", change.path)

            if isinstance(
                change, (yuio.git.SubmoduleStatus, yuio.git.UnmergedSubmoduleStatus)
            ):
                yuio.io.info(
                    "  (submodule%s%s%s)",
                    ", commit changed" if change.commit_changed else "",
                    ", has tracked changes" if change.has_tracked_changes else "",
                    ", has untracked changes" if change.has_untracked_changes else "",
                )
    else:
        yuio.io.info("No files were changed!")

    yuio.io.heading("Recent log")

    if log := repo.log(max_entries=5):
        for commit in log:
            yuio.io.info(
                "%s <c note>[%s <`%s`>]</c>",
                commit.title,
                commit.author,
                commit.author_email,
            )
    else:
        yuio.io.info("Log is empty!")
