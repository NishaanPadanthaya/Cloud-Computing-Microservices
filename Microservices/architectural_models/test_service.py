import requests
import base64
from PIL import Image
import io

def test_diagram_generation():
    # Test code with multiple classes and inheritance
    test_code = """
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        pass

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)
        self.breed = breed
    
    def speak(self):
        return "Woof!"
    
    def fetch(self):
        return "Fetching ball"

class Cat(Animal):
    def __init__(self, name, color):
        super().__init__(name)
        self.color = color
    
    def speak(self):
        return "Meow!"
    
    def scratch(self):
        return "Scratching post"
"""

    # Send request to the service
    response = requests.post(
        "http://localhost:8000/generate-diagram",
        json={"code": test_code}
    )
    
    if response.status_code == 200:
        # Get the base64 encoded diagram
        diagram_data = response.json()["diagram"]
        
        # Decode and save the image
        img_data = base64.b64decode(diagram_data)
        img = Image.open(io.BytesIO(img_data))
        img.save("class_diagram.png")
        print("Diagram generated and saved as 'class_diagram.png'")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    test_diagram_generation()