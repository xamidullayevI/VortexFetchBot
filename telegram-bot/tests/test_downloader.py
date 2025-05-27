import unittest
import os
from unittest.mock import patch
from bot.downloader import download_video_with_info, DownloadError

class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.test_url = "https://www.youtube.com/watch?v=test"
        self.test_dir = "test_downloads"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        # Test fayllarini tozalash
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)

    @patch('yt_dlp.YoutubeDL')
    def test_successful_download(self, mock_ytdl):
        # Mock setup
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {
            'title': 'Test Video',
            'duration': 120,
            'uploader': 'Test Channel'
        }
        mock_instance.prepare_filename.return_value = os.path.join(self.test_dir, 'test_video.mp4')

        # Test
        video_path, info = download_video_with_info(self.test_url, self.test_dir)
        
        self.assertIsNotNone(video_path)
        self.assertEqual(info['title'], 'Test Video')
        self.assertEqual(info['duration'], 120)

    @patch('yt_dlp.YoutubeDL')
    def test_download_error(self, mock_ytdl):
        # Mock setup
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("Download failed")

        # Test
        with self.assertRaises(DownloadError):
            download_video_with_info(self.test_url, self.test_dir)

if __name__ == '__main__':
    unittest.main()