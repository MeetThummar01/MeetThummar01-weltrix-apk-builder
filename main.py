import os
import threading
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import mainthread
import yt_dlp

class KivyLogger:
    def debug(self, msg): print(f"DEBUG: {msg}")
    def warning(self, msg): print(f"WARNING: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

class HomeScreen(Screen):
    def fetch_info_thread(self):
        url = self.ids.url_input.text
        if not url:
            self.ids.status_label.text = "Please enter a URL."
            return
        self.ids.fetch_button.disabled = True
        self.ids.status_label.text = "Fetching..."
        threading.Thread(target=self.fetch_info, args=(url,)).start()

    def fetch_info(self, url):
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'logger': KivyLogger()}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
            self.on_fetch_success(video_info)
        except Exception as e:
            self.on_fetch_error(f"Error: {e}")

    @mainthread
    def on_fetch_success(self, video_info):
        self.manager.get_screen('results').update_content(video_info)
        self.manager.current = 'results'
        self.ids.fetch_button.disabled = False
        self.ids.status_label.text = ""

    @mainthread
    def on_fetch_error(self, error_message):
        self.ids.status_label.text = error_message
        self.ids.fetch_button.disabled = False

class ResultsScreen(Screen):
    def update_content(self, video_info):
        self.video_info = video_info
        self.ids.thumbnail.source = self.video_info.get('thumbnail', '')
        self.ids.video_title_label.text = self.video_info.get('title', 'N/A')
        
        self.format_data = {}
        quality_tiers = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
        all_video_formats = [f for f in self.video_info.get('formats', []) if f.get('vcodec') != 'none' and f.get('height')]
        
        for height in quality_tiers:
            formats_for_tier = [f for f in all_video_formats if f.get('height') == height]
            if not formats_for_tier: continue
            best_format = max(formats_for_tier, key=lambda f: (f.get('fps', 0), f.get('tbr', 0)))
            desc = f"{height}p{best_format.get('fps', '') if best_format.get('fps', 0) > 30 else ''}"
            if desc not in self.format_data:
                self.format_data[desc] = {'format_id': best_format.get('format_id'), 'type': 'video'}
        
        if any(f.get('acodec') != 'none' for f in self.video_info.get('formats', [])):
            self.format_data["Audio Only MP3"] = {'type': 'audio'}
            
        self.ids.quality_spinner.values = list(self.format_data.keys())
        self.ids.quality_spinner.text = self.ids.quality_spinner.values[0] if self.ids.quality_spinner.values else 'No formats'
        self.ids.quality_spinner.disabled = False
        self.ids.download_button.disabled = False
        self.ids.status_label.text = "Ready to download."

    def toggle_trim_fields(self, value):
        self.ids.start_time_input.disabled = not value
        self.ids.end_time_input.disabled = not value

    def download_thread(self):
        try:
            from android.storage import primary_external_storage_path
            self.save_path = os.path.join(primary_external_storage_path(), 'Download')
        except ImportError:
            self.save_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
            
        self.ids.download_button.disabled = True
        threading.Thread(target=self.download_video).start()

    def download_video(self):
        try:
            selected_quality = self.ids.quality_spinner.text
            selected_format = self.format_data[selected_quality]
            format_type = selected_format['type']
            
            output_template = os.path.join(self.save_path, f"{yt_dlp.utils.sanitize_filename(self.video_info['title'])}.%(ext)s")
            
            ydl_opts = {'outtmpl': output_template, 'progress_hooks': [self.progress_hook], 'noprogress': True, 'logger': KivyLogger()}
            
            if self.ids.trim_checkbox.active:
                start, end = self.ids.start_time_input.text, self.ids.end_time_input.text
                ydl_opts['postprocessor_args'] = {'ffmpeg': ['-ss', start, '-to', end, '-c', 'copy']}
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
                ydl_opts['outtmpl'] = os.path.join(self.save_path, f"{yt_dlp.utils.sanitize_filename(self.video_info['title'])}_clip.%(ext)s")
            else:
                ydl_opts['merge_output_format'] = 'mp4'
                if format_type == 'audio':
                    ydl_opts['format'] = 'bestaudio/best'
                    ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
                else:
                    ydl_opts['format'] = f"{selected_format['format_id']}+bestaudio/best"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video_info['webpage_url']])
            
            self.on_download_complete()

        except Exception as e:
            self.update_status_on_main_thread(f"Download Error: {e}")
        finally:
            self.enable_download_button_on_main_thread()
            
    @mainthread
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                progress = d.get('downloaded_bytes', 0) / total_bytes
                self.ids.progress_bar.value = progress
                self.ids.status_label.text = f"Downloading... {int(progress*100)}%"
        elif d['status'] == 'finished':
            self.ids.status_label.text = "Finalizing..."
            
    @mainthread
    def on_download_complete(self):
        self.ids.status_label.text = f"Download Complete! Saved in Downloads folder."

    @mainthread
    def update_status_on_main_thread(self, text):
        self.ids.status_label.text = text
        
    @mainthread
    def enable_download_button_on_main_thread(self):
        self.ids.download_button.disabled = False

class MainScreenManager(ScreenManager):
    pass

class DownloaderApp(App):
    def build(self):
        # Kivy automatically loads the .kv file named after the app class (downloader.kv)
        return MainScreenManager()

if __name__ == '__main__':
    DownloaderApp().run()
