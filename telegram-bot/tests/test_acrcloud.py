import unittest
import os
from unittest.mock import patch, MagicMock
from bot.acrcloud_recognizer import extract_audio_from_video, get_music_info

class TestACRCloud(unittest.TestCase):
    def setUp(self):
        self.test_video = "test_video.mp4"
        self.test_audio = "test_audio.mp3"
        # Create dummy video file
        with open(self.test_video, "wb") as f:
            f.write(b"dummy video content")

    def tearDown(self):
        # Test fayllarini tozalash
        if os.path.exists(self.test_video):
            os.remove(self.test_video)
        if os.path.exists(self.test_audio):
            os.remove(self.test_audio)

    @patch('subprocess.run')
    def test_extract_audio(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        
        result = extract_audio_from_video(self.test_video, self.test_audio)
        
        self.assertEqual(result, self.test_audio)
        mock_run.assert_called_once()
        
        # Create dummy audio file to simulate successful extraction
        with open(self.test_audio, "wb") as f:
            f.write(b"dummy audio content")

    @patch('requests.post')
    @patch('os.getenv')
    def test_get_music_info(self, mock_getenv, mock_post):
        # Mock environment variables
        mock_getenv.side_effect = lambda x: {
            'ACRCLOUD_HOST': 'test.host',
            'ACRCLOUD_ACCESS_KEY': 'test_key',
            'ACRCLOUD_ACCESS_SECRET': 'test_secret'
        }.get(x)

        # Mock successful API response
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'status': {'code': 0},
                'metadata': {
                    'music': [{
                        'title': 'Test Song',
                        'artists': [{'name': 'Test Artist'}],
                        'album': {'name': 'Test Album'},
                        'release_date': '2023-01-01',
                        'external_metadata': {
                            'spotify': {'track': {'id': 'test_id'}},
                            'apple_music': {'url': 'test_url'}
                        }
                    }]
                }
            }
        )

        result = get_music_info(self.test_audio)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'Test Song')
        self.assertEqual(result['artist'], 'Test Artist')
        self.assertEqual(result['album'], 'Test Album')
        mock_post.assert_called_once()

    @patch('requests.post')
    @patch('os.getenv')
    def test_get_music_info_no_match(self, mock_getenv, mock_post):
        # Mock environment variables
        mock_getenv.side_effect = lambda x: {
            'ACRCLOUD_HOST': 'test.host',
            'ACRCLOUD_ACCESS_KEY': 'test_key',
            'ACRCLOUD_ACCESS_SECRET': 'test_secret'
        }.get(x)

        # Mock API response with no match
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'status': {'code': 0},
                'metadata': {'music': []}
            }
        )

        result = get_music_info(self.test_audio)
        self.assertIsNone(result)

    def test_get_music_info_missing_credentials(self):
        # Test when environment variables are not set
        with patch('os.getenv', return_value=None):
            result = get_music_info(self.test_audio)
            self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()