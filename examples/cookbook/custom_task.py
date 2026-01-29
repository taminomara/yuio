import time

import yuio.io
import yuio.theme
import yuio.widget

from typing import Never


class CustomTaskWidget(yuio.widget.Widget[Never]):  # [1]_
    def __init__(self, envs: list[str]) -> None:
        # All currently running environments.
        self.envs = envs

    def layout(self, rc: yuio.widget.RenderContext) -> tuple[int, int]:
        # Our widget always takes one line.
        return 1, 1  # [2]_

    def draw(self, rc: yuio.widget.RenderContext):  # [3]_
        if spinner_pattern := rc.get_msg_decoration("spinner/pattern"):
            # Draw spinner.
            rc.set_color_path("task/decoration:running")  # [4]_

            # `rc.spinner_state` is a timer synchronized with spinner update rate
            # configured in theme.
            spinner = spinner_pattern[rc.spinner_state % len(spinner_pattern)]
            rc.write(spinner)
            rc.move_pos(1, 0)

        # Draw running environments.
        sep = False
        for env in self.envs:
            if sep:
                rc.set_color_path("task:running")
                rc.write(" | ")
            rc.set_color_path("task/heading:running")
            rc.write(env)
            sep = True


class CustomTask(yuio.io.TaskBase):
    def __init__(self, envs: list[str] | None = None):
        super().__init__()

        # Our task widget implemented above.
        self._widget = CustomTaskWidget(envs or [])

    def _get_widget(self):
        # This method should return a widget.
        return self._widget

    def _get_priority(self):
        # This method should return an integer priority.
        return 1  # [1]_

    def add_env(self, env: str):
        with self._lock:  # All updates must happen under a lock.
            self._widget.envs.append(env)

            # Check if we're in foreground, and widgets are displayed.
            if self._widgets_are_displayed():
                # If so, notify background thread to update tasks sooner.
                self._request_update()
            else:
                # Otherwise, print the new status.
                yuio.io.info("%s started", env)

    def remove_env(self, env: str):
        with self._lock:
            self._widget.envs.remove(env)

            # Since printing redraws all tasks, we call `_request_update`
            # before `yuio.io.info`. This way, number of redraws is minimized.
            self._request_update()
            yuio.io.info("%s finished", env)

    def __enter__(self):
        # Attach this task to to the top level of the task tree to actually show it.
        # You don't have to do it in `__enter__`, you can do it anywhere you like.
        # For example, `yuio.io.Task` runs `attach` in its constructor.
        self.attach(None)  # [2]_
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Detach task from the task tree to hide it.
        self.detach()


class CustomTheme(yuio.theme.DefaultTheme):
    # For further authenticity, change spinner pattern to the one used in Tox.
    spinner_update_rate_ms = 100
    msg_decorations_unicode = {
        "spinner/pattern": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    }
    msg_decorations_ascii = {
        "spinner/pattern": "|-+x*",
    }


if __name__ == "__main__":
    env_list = ["3.14t", "3.14", "3.13", "3.12", "type", "lint"]

    yuio.io.setup(theme=CustomTheme)

    with CustomTask() as task:
        for env in env_list:
            task.add_env(env)
            time.sleep(0.2)

        time.sleep(5)

        for env in reversed(env_list):
            task.remove_env(env)
            time.sleep(0.2)

    yuio.io.success("Successfully tested %s", yuio.io.And(env_list))
