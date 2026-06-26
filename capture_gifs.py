import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import io

def create_gif(url, output_filename, frames_count=10, delay_ms=500, scroll_step=50):
    print(f"Generating GIF for {url} -> {output_filename}...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--window-size=1280,800')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(url)
        time.sleep(3) # Wait for initial load
        
        frames = []
        for i in range(frames_count):
            # Take screenshot
            png = driver.get_screenshot_as_png()
            img = Image.open(io.BytesIO(png))
            img = img.convert("RGB")
            frames.append(img)
            
            # Add some fake interactions so it looks like a video!
            if "8080" in url: # Jenkins
                try:
                    driver.execute_script("var el = document.querySelector('input[type=password]') || document.querySelector('input[name=j_password]'); if(el) el.value += '*';")
                except: pass
            elif "3001" in url: # Grafana
                try:
                    driver.execute_script("var el = document.querySelector('input[name=user]'); if(el) el.value += 'admin'[arguments[0] % 5];", i)
                except: pass
                
            # Scroll down slightly to create animation effect
            driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(delay_ms / 1000.0)
            
        # Save as GIF
        os.makedirs('assets', exist_ok=True)
        output_path = os.path.join('assets', output_filename)
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            optimize=True,
            duration=delay_ms,
            loop=0
        )
        print(f"Success: Saved {output_path}")
        
    except Exception as e:
        print(f"Error: Failed to generate {output_filename}: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    ip = "13.218.94.59"
    
    targets = [
        {"url": f"http://127.0.0.1:5000", "output": "dashboard_demo.gif", "frames": 15, "delay": 300, "scroll": 30},
        {"url": f"http://{ip}:3000", "output": "gitea_demo.gif", "frames": 10, "delay": 400, "scroll": 40},
        {"url": f"http://{ip}:8080", "output": "jenkins_demo.gif", "frames": 10, "delay": 400, "scroll": 0},
        {"url": f"http://{ip}:3001", "output": "grafana_demo.gif", "frames": 10, "delay": 400, "scroll": 0}
    ]
    
    for t in targets:
        create_gif(t['url'], t['output'], t['frames'], t['delay'], t['scroll'])
