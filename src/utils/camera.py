import gxipy as gx
from gxipy.gxidef import GxPixelFormatEntry, DxValidBit
import numpy as np
import cv2
from ctypes import *

class GalaxyCamera:
    def __init__(self, device_index=1):
        """Initialize the Galaxy camera controller.
        
        Args:
            device_index (int): Index of the camera device (default: 1)
        """
        self.device_index = device_index
        self.device_manager = None
        self.camera = None
        self.image_convert = None
        self.is_opened = False
        self._initialize_camera()

    def _initialize_camera(self):
        """Initialize camera and related objects."""
        try:
            self.device_manager = gx.DeviceManager()
            dev_num, dev_info_list = self.device_manager.update_all_device_list()
            if dev_num == 0:
                raise RuntimeError("No cameras found")

            # Open camera
            self.camera = self.device_manager.open_device_by_index(self.device_index)
            self.remote_device = self.camera.get_remote_device_feature_control()

            # Initialize image conversion
            self.image_convert = self.device_manager.create_image_format_convert()

            # Check if camera is color
            pixel_format_value, _ = self.remote_device.get_enum_feature("PixelFormat").get()
            if self._is_gray(pixel_format_value):
                raise RuntimeError("This implementation doesn't support mono cameras")

            # Configure camera for continuous acquisition
            self.remote_device.get_enum_feature("TriggerMode").set("Off")
            
            # Start streaming
            self.camera.stream_on()
            self.is_opened = True

        except Exception as e:
            self.release()
            raise RuntimeError(f"Failed to initialize camera: {str(e)}")

    def _is_gray(self, pixel_format):
        """Check if the pixel format is grayscale."""
        gray_formats = [
            GxPixelFormatEntry.MONO8,
            GxPixelFormatEntry.MONO10,
            GxPixelFormatEntry.MONO12,
            GxPixelFormatEntry.MONO14,
            GxPixelFormatEntry.MONO16
        ]
        return pixel_format in gray_formats

    def _get_best_valid_bits(self, pixel_format):
        """Get the best valid bits for the given pixel format."""
        if pixel_format in [GxPixelFormatEntry.MONO8, GxPixelFormatEntry.BAYER_GR8,
                           GxPixelFormatEntry.BAYER_RG8, GxPixelFormatEntry.BAYER_GB8,
                           GxPixelFormatEntry.BAYER_BG8, GxPixelFormatEntry.RGB8,
                           GxPixelFormatEntry.BGR8]:
            return DxValidBit.BIT0_7
        elif pixel_format in [GxPixelFormatEntry.MONO10, GxPixelFormatEntry.BAYER_GR10]:
            return DxValidBit.BIT2_9
        elif pixel_format in [GxPixelFormatEntry.MONO12, GxPixelFormatEntry.BAYER_GR12]:
            return DxValidBit.BIT4_11
        elif pixel_format == GxPixelFormatEntry.MONO14:
            return DxValidBit.BIT6_13
        elif pixel_format == GxPixelFormatEntry.MONO16:
            return DxValidBit.BIT8_15
        return DxValidBit.BIT0_7

    def _convert_to_rgb(self, raw_image):
        """Convert raw image to RGB format."""
        try:
            # Set conversion parameters
            self.image_convert.set_dest_format(GxPixelFormatEntry.RGB8)
            valid_bits = self._get_best_valid_bits(raw_image.get_pixel_format())
            self.image_convert.set_valid_bits(valid_bits)

            # Create output buffer
            buffer_size = self.image_convert.get_buffer_size_for_conversion(raw_image)
            output_buffer = (c_ubyte * buffer_size)()
            
            # Convert to RGB
            self.image_convert.convert(raw_image, addressof(output_buffer), buffer_size, False)
            
            return output_buffer, buffer_size
            
        except Exception as e:
            print(f"Error converting to RGB: {str(e)}")
            return None, 0

    def read(self):
        """Read a frame from the camera.
        
        Returns:
            tuple: (ret, frame) where ret is True if frame is valid, and frame is the BGR image
        """
        try:
            if not self.is_opened:
                return False, None

            # Get raw image
            raw_image = self.camera.data_stream[0].get_image()
            if raw_image is None:
                return False, None

            # Convert to RGB if necessary
            if raw_image.get_pixel_format() != GxPixelFormatEntry.RGB8:
                rgb_buffer, buffer_size = self._convert_to_rgb(raw_image)
                if rgb_buffer is None:
                    return False, None
                
                # Create numpy array
                numpy_image = np.frombuffer(rgb_buffer, dtype=np.uint8, count=buffer_size)
                numpy_image = numpy_image.reshape(raw_image.frame_data.height, 
                                               raw_image.frame_data.width, 3)
            else:
                numpy_image = raw_image.get_numpy_array()

            # Convert RGB to BGR for OpenCV compatibility
            bgr_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)
            return True, bgr_image

        except Exception as e:
            print(f"Error reading frame: {str(e)}")
            return False, None

    def isOpened(self):
        """Check if camera is opened."""
        return self.is_opened

    def release(self):
        """Release the camera resources."""
        if self.camera:
            self.camera.stream_off()
            self.camera.close_device()
        self.camera = None
        self.device_manager = None
        self.is_opened = False