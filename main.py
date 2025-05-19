import flet as ft
import os
import json
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from audio_silence_splitter import main as process_audio, find_speaking


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, process_file_callback, file_extensions):
        self.process_file_callback = process_file_callback
        self.file_extensions = file_extensions
        self.processed_files = set()

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            file_ext = os.path.splitext(file_path)[1].lower()

            if (
                file_ext in self.file_extensions
                and file_path not in self.processed_files
            ):
                self.processed_files.add(file_path)
                self.process_file_callback(file_path)


class AudioSplitterApp:
    def __init__(self):
        self.page = None
        self.settings_file = "audio_splitter_settings.json"
        self.default_settings = {
            "watch_folder": "",
            "output_folder": "",
            "name_template": "{filename}_clip_{index}",
            "trim_beg_end_only": False,
            "silence_min_len": 5,
            "volume_threshold": 0.01,
            "window_size": 1,
            "ease_in": 0.6,
            "normalization": False,
        }
        self.settings = self.load_settings()
        self.observer = None
        self.is_watching = False
        self.file_picker = None

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    return json.load(f)
            except:
                return self.default_settings.copy()
        return self.default_settings.copy()

    def save_settings(self):
        settings_to_save = {
            "watch_folder": self.watch_folder_text.value,
            "output_folder": self.output_folder_text.value,
            "name_template": self.name_template_text.value,
            "trim_beg_end_only": self.trim_beg_end_checkbox.value,
            "silence_min_len": float(
                self.silence_min_len_input.value
                if self.silence_min_len_input.value
                else 5
            ),
            "volume_threshold": float(
                self.volume_threshold_input.value
                if self.volume_threshold_input.value
                else 0.01
            ),
            "window_size": float(
                self.window_size_input.value if self.window_size_input.value else 1
            ),
            "ease_in": float(
                self.ease_in_input.value if self.ease_in_input.value else 0.6
            ),
            "normalization": self.normalization_checkbox.value,
        }

        with open(self.settings_file, "w") as f:
            json.dump(settings_to_save, f)

    def process_file(self, file_path):
        try:
            self.add_log(f"Processing file: {os.path.basename(file_path)}")

            # Get settings from UI
            output_folder = self.output_folder_text.value
            trim_beg_end_only = self.trim_beg_end_checkbox.value
            silence_min_len = float(
                self.silence_min_len_input.value
                if self.silence_min_len_input.value
                else 5
            )
            volume_threshold = float(
                self.volume_threshold_input.value
                if self.volume_threshold_input.value
                else 0.01
            )
            window_size = float(
                self.window_size_input.value if self.window_size_input.value else 1
            )
            ease_in = float(
                self.ease_in_input.value if self.ease_in_input.value else 0.6
            )
            normalization = self.normalization_checkbox.value

            # Create output folder if it doesn't exist
            if output_folder and not os.path.exists(output_folder):
                os.makedirs(output_folder, exist_ok=True)

            # Get the original file info
            original_basename = os.path.basename(file_path)
            original_name = os.path.splitext(original_basename)[0]

            # Determine output path based on settings
            if output_folder:
                processing_folder = output_folder
            else:
                processing_folder = os.path.join(
                    os.path.dirname(file_path), "processed"
                )

            os.makedirs(processing_folder, exist_ok=True)

            # Set output name
            if trim_beg_end_only:
                # If only trimming beginning and end, use original name
                output_name = f"{original_name}.mp3"
            else:
                # Use template for multiple clips
                name_template = self.name_template_text.value
                if not name_template:
                    name_template = "{filename}_clip_{index}"
                # The template will be used in the main function
                output_name = name_template

            output_path = os.path.join(processing_folder, output_name)

            # Check if output file already exists
            if os.path.exists(output_path):
                self.add_log(f"Skipping file {file_path}, output file already exists")
                return

            # Process the file using the main function from audio_silence_splitter
            # Run in a separate thread to avoid blocking the UI
            threading.Thread(
                target=self._process_file_thread,
                args=(
                    file_path,
                    output_path,
                    trim_beg_end_only,
                    silence_min_len,
                    volume_threshold,
                    window_size,
                    ease_in,
                    normalization,
                ),
                daemon=True,
            ).start()

        except Exception as e:
            self.add_log(
                f"Error setting up processing for {os.path.basename(file_path)}: {str(e)}"
            )

    def _process_file_thread(
        self,
        file_path,
        output_path,
        beg_end_only,
        silence_min_len,
        volume_threshold,
        window_size,
        ease_in,
        normalization,
    ):
        try:
            # Call the main function from audio_silence_splitter
            result_folder = process_audio(
                file_in=file_path,
                output_path=output_path,
                NORMALIZATION=normalization,
                BEG_END_only=beg_end_only,
                silence_min_len=silence_min_len,
                volume_threshold=volume_threshold,
                window_size=window_size,
                ease_in=ease_in,
            )

            # Log completion
            # Need to use page.update since we're in a different thread
            self.add_log(
                f"Completed processing: {os.path.basename(file_path)} → {result_folder}"
            )

        except Exception as e:
            self.add_log(f"Error processing {os.path.basename(file_path)}: {str(e)}")

    def start_watching(self):
        if self.is_watching:
            self.add_log("Already watching folder")
            return

        folder_path = self.watch_folder_text.value
        if not folder_path or not os.path.exists(folder_path):
            self.add_log("Please select a valid folder to watch")
            return

        try:
            self.observer = Observer()
            event_handler = FileEventHandler(
                self.process_file,
                [".mp4", ".webm", ".mov", ".avi", ".mp3", ".wav", ".ogg", ".flac"],
            )
            self.observer.schedule(event_handler, folder_path, recursive=False)
            self.observer.start()
            self.is_watching = True
            self.watch_button.text = "Stop Watching"
            self.watch_button.bgcolor = ft.colors.RED_400
            self.page.update()
            self.add_log(f"Started watching folder: {folder_path}")
        except Exception as e:
            self.add_log(f"Error starting watcher: {str(e)}")

    def stop_watching(self):
        if not self.is_watching:
            return

        try:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.is_watching = False
            self.watch_button.text = "Start Watching"
            self.watch_button.bgcolor = ft.colors.BLUE_400
            self.page.update()
            self.add_log("Stopped watching folder")
        except Exception as e:
            self.add_log(f"Error stopping watcher: {str(e)}")

    def toggle_watching(self, e):
        if self.is_watching:
            self.stop_watching()
        else:
            self.start_watching()

    def pick_folder(self, text_field, e):
        def update_text_field(result):
            if result is not None and result.path:
                text_field.value = result.path
                self.page.update()
                self.save_settings()

        if not self.file_picker:
            self.file_picker = ft.FilePicker(on_result=update_text_field)
            self.page.overlay.append(self.file_picker)
            self.page.update()

        self.file_picker.on_result = update_text_field
        self.file_picker.get_directory_path()

    def pick_file(self, e):
        def update_file_field(result):
            if result is not None and result.files:
                for file_path in result.files:
                    self.process_file(file_path.path)

        if not self.file_picker:
            self.file_picker = ft.FilePicker(on_result=update_file_field)
            self.page.overlay.append(self.file_picker)
            self.page.update()

        self.file_picker.on_result = update_file_field
        self.file_picker.pick_files(
            allowed_extensions=[
                "mp4",
                "webm",
                "mov",
                "avi",
                "mp3",
                "wav",
                "ogg",
                "flac",
            ],
            allow_multiple=True,
        )

    def add_log(self, message):
        current_time = time.strftime("%H:%M:%S")
        self.log_text.value = f"{current_time} - {message}\n" + self.log_text.value
        self.page.update()

    def init_ui(self, page):
        self.page = page
        page.title = "Audio Silence Splitter"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 900
        page.window_height = 700
        page.window_min_width = 800
        page.window_min_height = 600

        # Create UI elements
        self.watch_folder_text = ft.TextField(
            label="Watch Folder",
            value=self.settings["watch_folder"],
            expand=True,
            tooltip="Folder to watch for new audio/video files",
        )

        self.output_folder_text = ft.TextField(
            label="Output Folder",
            value=self.settings["output_folder"],
            expand=True,
            tooltip="Where to save processed MP3 files",
        )

        self.name_template_text = ft.TextField(
            label="Filename Template",
            value=self.settings["name_template"],
            expand=True,
            hint_text="{filename}_clip_{index}",
            tooltip="Template for output filenames. Available variables: {filename}, {index}, {start}, {end}",
        )

        self.trim_beg_end_checkbox = ft.Checkbox(
            label="Trim Beginning and End Only",
            value=self.settings["trim_beg_end_only"],
            tooltip="When checked, will only trim start and end silence",
        )

        self.normalization_checkbox = ft.Checkbox(
            label="Apply Audio Normalization",
            value=self.settings["normalization"],
            tooltip="Apply audio normalization during processing",
        )

        self.watch_button = ft.ElevatedButton(
            text="Start Watching",
            bgcolor=ft.colors.BLUE_400,
            color=ft.colors.WHITE,
            on_click=self.toggle_watching,
            icon=ft.icons.VISIBILITY,
        )

        self.process_file_button = ft.ElevatedButton(
            text="Process Files",
            bgcolor=ft.colors.GREEN_400,
            color=ft.colors.WHITE,
            on_click=self.pick_file,
            icon=ft.icons.FILE_OPEN,
        )

        self.log_text = ft.TextField(
            label="Log",
            multiline=True,
            read_only=True,
            min_lines=12,
            max_lines=12,
            expand=True,
        )

        # Advanced settings - numeric inputs instead of sliders
        self.silence_min_len_input = ft.TextField(
            label="Silence Minimum Length (min)",
            value=str(self.settings["silence_min_len"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.RIGHT,
            width=150,
            hint_text="5",
        )

        self.volume_threshold_input = ft.TextField(
            label="Volume Threshold",
            value=str(self.settings["volume_threshold"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.RIGHT,
            width=150,
            hint_text="0.01",
        )

        self.window_size_input = ft.TextField(
            label="Window Size (seconds)",
            value=str(self.settings["window_size"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.RIGHT,
            width=150,
            hint_text="1.0",
        )

        self.ease_in_input = ft.TextField(
            label="Ease In/Out (seconds)",
            value=str(self.settings["ease_in"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.RIGHT,
            width=150,
            hint_text="0.6",
        )

        # Set up tabs
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Main Settings",
                    icon=ft.icons.SETTINGS,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        self.watch_folder_text,
                                        ft.IconButton(
                                            icon=ft.icons.FOLDER_OPEN,
                                            tooltip="Select Watch Folder",
                                            on_click=lambda e: self.pick_folder(
                                                self.watch_folder_text, e
                                            ),
                                        ),
                                    ]
                                ),
                                ft.Row(
                                    [
                                        self.output_folder_text,
                                        ft.IconButton(
                                            icon=ft.icons.FOLDER_OPEN,
                                            tooltip="Select Output Folder",
                                            on_click=lambda e: self.pick_folder(
                                                self.output_folder_text, e
                                            ),
                                        ),
                                    ]
                                ),
                                self.name_template_text,
                                ft.Row(
                                    [
                                        self.trim_beg_end_checkbox,
                                        self.normalization_checkbox,
                                    ]
                                ),
                                ft.Row([self.watch_button, self.process_file_button]),
                            ]
                        ),
                        padding=20,
                    ),
                ),
                ft.Tab(
                    text="Advanced Settings",
                    icon=ft.icons.TUNE,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Silence Detection Parameters",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Row(
                                    [
                                        self.silence_min_len_input,
                                        ft.Text(
                                            "Minimum length of silence to be considered a break",
                                            size=12,
                                            italic=True,
                                        ),
                                    ]
                                ),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        self.volume_threshold_input,
                                        ft.Text(
                                            "Volume below this threshold is considered silence",
                                            size=12,
                                            italic=True,
                                        ),
                                    ]
                                ),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        self.window_size_input,
                                        ft.Text(
                                            "Size of window for analyzing silence",
                                            size=12,
                                            italic=True,
                                        ),
                                    ]
                                ),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        self.ease_in_input,
                                        ft.Text(
                                            "Buffer to add before and after speech",
                                            size=12,
                                            italic=True,
                                        ),
                                    ]
                                ),
                                ft.FilledButton(
                                    text="Save Settings",
                                    on_click=lambda _: self.save_settings(),
                                ),
                            ]
                        ),
                        padding=20,
                    ),
                ),
                ft.Tab(
                    text="Logs",
                    icon=ft.icons.HISTORY,
                    content=ft.Container(
                        content=ft.Column(
                            [
                                self.log_text,
                                ft.FilledButton(
                                    text="Clear Log",
                                    on_click=lambda _: setattr(
                                        self.log_text, "value", ""
                                    )
                                    or self.page.update(),
                                ),
                            ]
                        ),
                        padding=20,
                    ),
                ),
            ],
        )

        # Construct the page
        page.add(
            ft.AppBar(
                title=ft.Text("Audio Silence Splitter"),
                center_title=True,
                bgcolor=ft.colors.SURFACE_VARIANT,
            ),
            tabs,
        )

        # Initialize file picker
        self.file_picker = ft.FilePicker()
        page.overlay.append(self.file_picker)

        # Add initial log entry
        self.add_log("Application started")

    def main(self):
        ft.app(target=self.init_ui)


if __name__ == "__main__":
    app = AudioSplitterApp()
    app.main()
