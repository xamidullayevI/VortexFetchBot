import unittest
import os
from unittest.mock import patch, MagicMock
from bot.video_compress import compress_video, get_video_info, calculate_bitrate

class TestVideoCompress(unittest.TestCase):
    def setUp(self):
        self.test_input = "test_input.mp4"
        self.test_output = "test_output.mp4"
        # Create dummy input file
        with open(self.test_input, "wb") as f:
            f.write(b"dummy video content")

    def tearDown(self):
        # Test fayllarini tozalash
        if os.path.exists(self.test_input):
            os.remove(self.test_input)
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    @patch('ffmpeg.probe')
    @patch('ffmpeg.input')
    @patch('ffmpeg.run')
    def test_compress_video(self, mock_run, mock_input, mock_probe):
        # Mock setup
        mock_probe.return_value = {
            'format': {'duration': '60'},
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }
        mock_input.return_value = MagicMock()
        mock_input.return_value.output.return_value = MagicMock()
        mock_input.return_value.output.return_value.overwrite_output.return_value = MagicMock()
        
        # Create dummy output file to simulate successful compression
        with open(self.test_output, "wb") as f:
            f.write(b"compressed content")

        result = compress_video(self.test_input, self.test_output, target_size_mb=45)
        
        self.assertIsNotNone(result)
        self.assertEqual(result, self.test_output)
        mock_probe.assert_called_once()
        mock_input.assert_called_once()

    def test_calculate_bitrate(self):
        # Test bitrate calculation
        duration = 60  # 1 minute
        target_size_mb = 45
        expected_bitrate = (target_size_mb * 8 * 1024 * 1024) // duration
        
        result = calculate_bitrate(target_size_mb, duration)
        
        self.assertEqual(result, expected_bitrate)
        self.assertGreaterEqual(result, 100 * 1024)  # Should be at least 100kbps

    @patch('ffmpeg.probe')
    def test_get_video_info(self, mock_probe):
        # Mock setup
        mock_probe.return_value = {
            'format': {'duration': '60'},
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080}]
        }

        duration, width, height = get_video_info(self.test_input)
        
        self.assertEqual(duration, 60)
        self.assertEqual(width, 1920)
        self.assertEqual(height, 1080)

    def test_invalid_input_path(self):
        result = compress_video("nonexistent.mp4", self.test_output)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()