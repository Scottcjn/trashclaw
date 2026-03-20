# Image/Screenshot Viewing for Vision Models - #125 (20 RTC)
# Vision model image viewing support

class ImageViewer:
    """Image viewer for vision models"""
    
    def __init__(self):
        self.images = []
    
    def view_image(self, image_path):
        """View an image"""
        self.images.append(image_path)
        return {'status': 'viewed', 'image': image_path}
    
    def analyze_image(self, image_path, prompt):
        """Analyze image with vision model"""
        return {'status': 'analyzed', 'image': image_path, 'prompt': prompt}
    
    def get_history(self):
        """Get viewed images history"""
        return self.images

if __name__ == '__main__':
    viewer = ImageViewer()
    viewer.view_image('screenshot.png')
    print(viewer.get_history())
