from PIL import Image, ImageDraw, ImageFont
import os
import random
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import glob
from main import show_loading_throbber

def create_character_image_worker(args):
    """Worker function for multiprocessing character image creation"""
    char, folder_name, font_path, font_name, output_base_dir, size, apply_rotation = args
    
    try:
        # Load font
        font = ImageFont.truetype(font_path, 32)
        
        # Create folder for this character
        char_dir = os.path.join(output_base_dir, folder_name)
        os.makedirs(char_dir, exist_ok=True)
        
        # Create image with padding to prevent cutoff during rotation
        padding = 8 if apply_rotation else 0  # Only add padding if rotation is enabled
        padded_size = (size + padding, size + padding)
        img = Image.new("L", padded_size, color="white")
        draw = ImageDraw.Draw(img)
        
        # Get size of text to center it
        bbox = draw.textbbox((0, 0), char, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((padding//2-bbox[0]+((size-text_width)//2)),
                   (padding//2-bbox[1]+((size-text_height)//2)))
        
        # Draw the character
        draw.text(position, char, fill="black", font=font)
        
        # Apply random rotation of ±20 degrees if enabled
        if apply_rotation:
            rotation_angle = random.uniform(-20, 20)
            img = img.rotate(rotation_angle, expand=True, fillcolor="white")
        
        # Crop to final size, ensuring we get the center portion
        img_width, img_height = img.size
        left = (img_width - size) // 2
        top = (img_height - size) // 2
        right = left + size
        bottom = top + size
        img = img.crop((left, top, right, bottom))
        
        # Determine filename
        if char.isalpha():
            case_prefix = 'lower' if char.islower() else 'upper'
            safe_name = f"{case_prefix}{char.upper()}"
        elif char in ['!', '@', '#', '$', '%', '&', '*', '+', '-', '?', '<', '>']:
            symwords = ['exclmark', 'at', 'hash', 'dollar', 'percent', 'ampersand', 
                       'asterisk', 'plus', 'minus', 'quesmark', 'lessthan', 'greaterthan']
            symbol_index = ['!', '@', '#', '$', '%', '&', '*', '+', '-', '?', '<', '>'].index(char)
            safe_name = symwords[symbol_index]
        else:
            safe_name = f"{char}"
            
        filename = f"{font_name}_{safe_name}.png"
        img.save(os.path.join(char_dir, filename))
        return True
        
    except Exception as e:
        print(f"Error creating image for {char} with font {font_name}: {str(e)}")
        return False

class CharacterImageGenerator:
    def __init__(self):
        # Settings
        self.size = 28
        self.img_size = (self.size, self.size)
        self.font_size = 28

        # Define the base output and fonts directories
        root_dir = os.path.dirname(os.path.dirname(__file__))
        self.output_base_dir = os.path.join(root_dir, "content", "data", "generated_images")
        self.fonts_dir = os.path.join(root_dir, "content", "fonts")

        # Create base output directory structure
        os.makedirs(self.output_base_dir, exist_ok=True)

        # Character sets
        self.symbols = ['!', '@', '#', '$', '%', '&', '*', '+', '-', '?', '<', '>']
        self.symwords = ['exclmark', 'at', 'hash', 'dollar', 'percent', 'ampersand', 
                    'asterisk', 'plus', 'minus', 'quesmark', 'lessthan', 'greaterthan']

        self.upperLetters = [chr(i) for i in range(65,91)]
        self.lowerLetters = [chr(i) for i in range(97,123)]
        self.numbers = [chr(i) for i in range(48,58)]
        self.characters = self.upperLetters + self.lowerLetters + self.numbers

    def create_character_image(self, char, folder_name, font, font_name, apply_rotation=True):
        # Create folder for this character in base output directory
        char_dir = os.path.join(self.output_base_dir, folder_name)
        os.makedirs(char_dir, exist_ok=True)
        
        # Create image with padding to prevent cutoff during rotation
        padding = 8 if apply_rotation else 0  # Only add padding if rotation is enabled
        padded_size = (self.size + padding, self.size + padding)
        img = Image.new("L", padded_size, color="white")
        draw = ImageDraw.Draw(img)
        
        # Get size of text to center it
        bbox = draw.textbbox((0, 0), char, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((padding//2-bbox[0]+((self.size-text_width)//2)),
                   (padding//2-bbox[1]+((self.size-text_height)//2)))
        
        # Draw the character
        draw.text(position, char, fill="black", font=font)
        
        # Apply random rotation of ±20 degrees if enabled
        if apply_rotation:
            rotation_angle = random.uniform(-20, 20)
            img = img.rotate(rotation_angle, expand=True, fillcolor="white")
        
        # Crop to final size, ensuring we get the center portion
        img_width, img_height = img.size
        left = (img_width - self.size) // 2
        top = (img_height - self.size) // 2
        right = left + self.size
        bottom = top + self.size
        img = img.crop((left, top, right, bottom))
        
        # Save image using case-specific folder names
        if char.isalpha():
            case_prefix = 'lower' if char.islower() else 'upper'
            safe_name = f"{case_prefix}{char.upper()}"
        elif char in self.symbols:
            symbol_index = self.symbols.index(char)
            safe_name = self.symwords[symbol_index]
        else:
            safe_name = f"{char}"
            
        filename = f"{font_name}_{safe_name}.png"
        img.save(os.path.join(char_dir, filename))

    def generateImages(self, apply_rotation=True):
        """Optimized image generation with multiprocessing"""
        print("[INFO] Preparing to generate images. This may take a while...")
        show_loading_throbber("Generating images", duration=1.0)
        # Get all font files from fonts directory
        font_files = [f for f in os.listdir(self.fonts_dir) if f.endswith(('.woff2', '.ttf', 'otf'))]
        
        if not font_files:
            print("No font files found!")
            return
        
        print(f"Found {len(font_files)} font files. Generating images...")
        print(f"[INFO] Random rotation: {'Enabled (±20°)' if apply_rotation else 'Disabled'}")
        start_time = time.time()
        
        # Prepare all tasks
        all_tasks = []
        total_images = 0
        
        for font_file in font_files:
            font_path = os.path.join(self.fonts_dir, font_file)
            font_name = os.path.splitext(font_file)[0]
            
            # Process all characters
            for char in self.characters:
                if char.isalpha():
                    case_prefix = 'lower' if char.islower() else 'upper'
                    folder_name = f"{case_prefix}{char.upper()}"
                else:
                    folder_name = f"{char}"
                
                all_tasks.append((char, folder_name, font_path, font_name, self.output_base_dir, self.size, apply_rotation))
                total_images += 1

            # Process symbols
            for sym, word in zip(self.symbols, self.symwords):
                all_tasks.append((sym, word, font_path, font_name, self.output_base_dir, self.size, apply_rotation))
                total_images += 1
        
        print(f"Total images to generate: {total_images}")

        # Use single-threaded processing for small task sets
        if len(all_tasks) <= 100:
            print("Small task set detected (<=100 tasks). Using single-threaded processing.")
            successful_images = 0
            for i, task in enumerate(all_tasks):
                result = create_character_image_worker(task)
                if result:
                    successful_images += 1
                # Progress update every 10 images
                if (i + 1) % 10 == 0 or (i + 1) == len(all_tasks):
                    progress = ((i + 1) / len(all_tasks)) * 100
                    elapsed = time.time() - start_time
                    print(f"Progress: {progress:.1f}% ({i + 1}/{len(all_tasks)} images) - {elapsed:.1f}s elapsed")
        else:
            # Conservative multiprocessing configuration for system-friendly operation
            # Use only 2 processes maximum to reduce system load
            num_processes = min(2, mp.cpu_count() // 2)  # Use at most 2 processes or half of CPU cores
            if num_processes < 1:
                num_processes = 1
            
            # Larger batch sizes to reduce overhead and memory pressure
            batch_size = max(50, len(all_tasks) // (num_processes * 2))  # Larger batches, fewer total
            print(f"Using {num_processes} process(es) with batch size {batch_size}")
            
            # Split tasks into batches
            batches = [all_tasks[i:i + batch_size] for i in range(0, len(all_tasks), batch_size)]
            
            # Process batches in parallel with limited concurrency
            successful_images = 0
            try:
                with ProcessPoolExecutor(max_workers=num_processes) as executor:
                    # Submit batches one at a time to limit memory usage
                    futures = []
                    completed = 0
                    
                    for i, batch in enumerate(batches):
                        # Submit batch
                        future = executor.submit(self._process_batch, batch)
                        futures.append(future)
                        
                        # Wait for completion if we have too many pending futures
                        # This prevents memory buildup and reduces system load
                        if len(futures) >= num_processes:
                            # Wait for one future to complete
                            done_future = futures.pop(0)
                            try:
                                batch_results = done_future.result()
                                successful_images += sum(batch_results)
                                completed += 1
                            except Exception as e:
                                print(f"[WARNING] Batch processing failed: {e}")
                            
                            # Progress update
                            if completed % max(1, len(batches) // 10) == 0 or completed % 5 == 0:
                                progress = (completed / len(batches)) * 100
                                elapsed = time.time() - start_time
                                print(f"Progress: {progress:.1f}% ({completed}/{len(batches)} batches) - {elapsed:.1f}s elapsed")
                    
                    # Wait for remaining futures
                    for future in futures:
                        try:
                            batch_results = future.result()
                            successful_images += sum(batch_results)
                            completed += 1
                        except Exception as e:
                            print(f"[WARNING] Batch processing failed: {e}")
                        
                        # Final progress updates
                        if completed % max(1, len(batches) // 10) == 0 or completed % 5 == 0:
                            progress = (completed / len(batches)) * 100
                            elapsed = time.time() - start_time
                            print(f"Progress: {progress:.1f}% ({completed}/{len(batches)} batches) - {elapsed:.1f}s elapsed")
                            
            except Exception as e:
                print(f"Multiprocessing failed: {e}")
                print("Falling back to single-threaded processing...")
                for i, task in enumerate(all_tasks):
                    result = create_character_image_worker(task)
                    if result:
                        successful_images += 1
                    # Progress update every 100 images
                    if (i + 1) % 100 == 0:
                        progress = ((i + 1) / len(all_tasks)) * 100
                        elapsed = time.time() - start_time
                        print(f"Progress: {progress:.1f}% ({i + 1}/{len(all_tasks)} images) - {elapsed:.1f}s elapsed")
        
        total_time = time.time() - start_time
        print(f"Generated {successful_images}/{total_images} images in {total_time:.2f} seconds")
        print(f"Average time per image: {total_time/total_images*1000:.2f} ms")
    
    def _process_batch(self, batch):
        """Process a batch of image creation tasks"""
        results = []
        for task in batch:
            result = create_character_image_worker(task)
            results.append(result)
        return results