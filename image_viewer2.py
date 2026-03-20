# Image/Screenshot Viewing - #65 (20 RTC)

class ImageViewer:
    def __init__(self):
        self.images = []
    
    def view(self, path):
        self.images.append(path)
        return {'status': 'viewed'}

if __name__ == '__main__':
    viewer = ImageViewer()
    viewer.view('test.png')
    print(viewer.images)
