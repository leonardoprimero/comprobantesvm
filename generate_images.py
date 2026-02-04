from PIL import Image, ImageDraw
import os

def create_gradient(width, height, start_color, end_color):
    base = Image.new('RGB', (width, height), start_color)
    top = Image.new('RGB', (width, height), end_color)
    mask = Image.new('L', (width, height))
    mask_data = []
    for y in range(height):
        for x in range(width):
            mask_data.append(int(255 * (y / height)))
    mask.putdata(mask_data)
    base.paste(top, (0, 0), mask)
    return base

def create_installer_images():
    # Colors
    teal_dark = (13, 92, 90)    # #0D5C5A
    teal_light = (26, 138, 135) # #1A8A87
    white = (255, 255, 255)

    # 1. Sidebar Image (WizardImageFile) - typically 164x314 or similar ratio
    # Making it high res: 328x628
    width, height = 328, 628
    img_large = create_gradient(width, height, teal_dark, teal_light)
    draw_large = ImageDraw.Draw(img_large)
    
    # Add some geometric accents
    draw_large.rectangle([0, 0, 20, height], fill=teal_dark)
    draw_large.ellipse([width-100, height-100, width+50, height+50], fill=(255, 255, 255, 30))
    draw_large.ellipse([20, 20, 150, 150], fill=(255, 255, 255, 20))
    
    output_dir = r"c:\Users\Leonardo\Downloads\innosetup-main\innosetup-main\installer\resources"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    img_large.save(os.path.join(output_dir, "installer_sidebar_large.bmp"))
    print("Created installer_sidebar_large.bmp")

    # 2. Small Header Image (WizardSmallImageFile) - typically 55x55
    # Making it 110x110
    s_width, s_height = 110, 110
    img_small = Image.new('RGB', (s_width, s_height), teal_dark)
    draw_small = ImageDraw.Draw(img_small)
    
    # Simple icon
    margin = 20
    draw_small.rectangle([margin, margin, s_width-margin, s_height-margin], outline=white, width=4)
    draw_small.line([margin, s_height//2, s_width-margin, s_height//2], fill=white, width=2)
    draw_small.line([s_width//2, margin, s_width//2, s_height-margin], fill=white, width=2)

    img_small.save(os.path.join(output_dir, "installer_header_small.bmp"))
    print("Created installer_header_small.bmp")

if __name__ == "__main__":
    create_installer_images()
