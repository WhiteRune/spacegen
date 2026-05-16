#!/usr/bin/env python3
"""
GUI launcher for video generation pipeline using tkinter.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import os
import json
import sys
from pathlib import Path
import threading

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class VideoGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Generation Pipeline")
        self.root.geometry("700x1000")
        self.root.resizable(True, True)
        
        # Track subprocess
        self.current_process = None
        self.is_generating = False
        self.voice_process = None
        self.is_generating_voice = False
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="🎬 Video Generation Pipeline", font=("Arial", 18, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Topic
        ttk.Label(main_frame, text="Topic:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.topic_var = tk.StringVar(value="neutron stars")
        topic_entry = ttk.Entry(main_frame, textvariable=self.topic_var, width=40)
        topic_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Length in seconds
        ttk.Label(main_frame, text="Duration (seconds):", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.length_var = tk.IntVar(value=60)
        length_spinbox = ttk.Spinbox(main_frame, from_=15, to=300, textvariable=self.length_var, width=10)
        length_spinbox.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Scenes count
        ttk.Label(main_frame, text="Number of Scenes:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.scenes_var = tk.IntVar(value=4)
        scenes_spinbox = ttk.Spinbox(main_frame, from_=2, to=10, textvariable=self.scenes_var, width=10)
        scenes_spinbox.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Retrieval limit
        ttk.Label(main_frame, text="Retrieval Limit:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.retrieval_var = tk.IntVar(value=5)
        retrieval_spinbox = ttk.Spinbox(main_frame, from_=1, to=20, textvariable=self.retrieval_var, width=10)
        retrieval_spinbox.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Enable reasoning checkbox
        self.reasoning_var = tk.BooleanVar(value=False)
        reasoning_check = ttk.Checkbutton(main_frame, text="Enable Reasoning (slower, more accurate)", variable=self.reasoning_var)
        reasoning_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Retrieved docs file
        ttk.Label(main_frame, text="Retrieved Docs (optional):", font=("Arial", 10, "bold")).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.docs_var = tk.StringVar(value="")
        docs_frame = ttk.Frame(main_frame)
        docs_frame.grid(row=6, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        docs_entry = ttk.Entry(docs_frame, textvariable=self.docs_var, width=30)
        docs_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        docs_button = ttk.Button(docs_frame, text="Browse", command=self.browse_docs)
        docs_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Output directory
        ttk.Label(main_frame, text="Output Directory:", font=("Arial", 10, "bold")).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.output_var = tk.StringVar(value="./output")
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=7, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_var, width=30)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        output_button = ttk.Button(output_frame, text="Browse", command=self.browse_output)
        output_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        
        # Generate and Cancel buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=9, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.generate_button = ttk.Button(button_frame, text="🚀 Generate Video Package", command=self.generate)
        self.generate_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.cancel_button = ttk.Button(button_frame, text="⛔ Cancel", command=self.cancel_generation, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        
        # Extract narration button
        extract_button = ttk.Button(main_frame, text="📝 Extract Narration (after generation)", command=self.extract_narration)
        extract_button.grid(row=11, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        # Separator
        ttk.Separator(main_frame, orient='horizontal').grid(row=12, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=15)
        
        # Voice settings section
        ttk.Label(main_frame, text="🎙️ Voice Generation Settings", font=("Arial", 12, "bold")).grid(row=13, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Voice selection
        ttk.Label(main_frame, text="Voice:", font=("Arial", 10, "bold")).grid(row=14, column=0, sticky=tk.W, pady=5)
        self.voice_var = tk.StringVar(value="Charon")
        voice_combo = ttk.Combobox(main_frame, textvariable=self.voice_var, 
                                   values=["Charon", "Aoede", "Ember", "Lira", "Orion", "Sage"],
                                   state="readonly", width=20)
        voice_combo.grid(row=14, column=1, sticky=tk.W, pady=5)
        
        # Speech speed
        ttk.Label(main_frame, text="Speed:", font=("Arial", 10, "bold")).grid(row=15, column=0, sticky=tk.W, pady=5)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_spinbox = ttk.Spinbox(main_frame, from_=0.5, to=2.0, increment=0.1, textvariable=self.speed_var, width=10)
        speed_spinbox.grid(row=15, column=1, sticky=tk.W, pady=5)
        
        # Voice output directory
        ttk.Label(main_frame, text="Voice Output Dir:", font=("Arial", 10, "bold")).grid(row=16, column=0, sticky=tk.W, pady=5)
        self.voice_output_var = tk.StringVar(value="./output/voice_over")
        voice_output_frame = ttk.Frame(main_frame)
        voice_output_frame.grid(row=16, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        voice_output_entry = ttk.Entry(voice_output_frame, textvariable=self.voice_output_var, width=30)
        voice_output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        voice_output_button = ttk.Button(voice_output_frame, text="Browse", command=self.browse_voice_output)
        voice_output_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Generate voice button
        voice_button_frame = ttk.Frame(main_frame)
        voice_button_frame.grid(row=17, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
        
        self.generate_voice_button = ttk.Button(voice_button_frame, text="🎙️ Generate Voice Over", command=self.generate_voice)
        self.generate_voice_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.cancel_voice_button = ttk.Button(voice_button_frame, text="⛔ Cancel Voice", command=self.cancel_voice_generation, state=tk.DISABLED)
        self.cancel_voice_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        # Status text area
        ttk.Label(main_frame, text="Status:", font=("Arial", 10, "bold")).grid(row=18, column=0, sticky=tk.W, pady=(10, 5))
        self.status_text = scrolledtext.ScrolledText(main_frame, height=15, width=70, state=tk.DISABLED)
        self.status_text.grid(row=19, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(19, weight=1)
    
    def log(self, message: str):
        """Add message to status text area."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.root.update()
    
    def browse_docs(self):
        """Browse for retrieved documents JSON file."""
        file_path = filedialog.askopenfilename(
            title="Select Retrieved Documents JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.docs_var.set(file_path)
    
    def browse_output(self):
        """Browse for output directory."""
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_var.set(dir_path)
    
    def browse_voice_output(self):
        """Browse for voice output directory."""
        dir_path = filedialog.askdirectory(title="Select Voice Output Directory")
        if dir_path:
            self.voice_output_var.set(dir_path)
    
    def cancel_generation(self):
        """Cancel the running generation process."""
        if self.current_process and self.current_process.poll() is None:
            self.log("")
            self.log("🛑 Cancelling generation...")
            self.current_process.terminate()
            
            # Wait for process to terminate
            try:
                self.current_process.wait(timeout=5)
                self.log("✋ Generation cancelled by user")
            except subprocess.TimeoutExpired:
                self.log("⚠️ Force killing process...")
                self.current_process.kill()
                self.current_process.wait()
                self.log("✋ Generation forcefully stopped")
            
            self.is_generating = False
            self._update_button_states()
    
    def cancel_voice_generation(self):
        """Cancel the running voice generation process."""
        if self.voice_process and self.voice_process.poll() is None:
            self.log("")
            self.log("🛑 Cancelling voice generation...")
            self.voice_process.terminate()
            
            # Wait for process to terminate
            try:
                self.voice_process.wait(timeout=5)
                self.log("✋ Voice generation cancelled by user")
            except subprocess.TimeoutExpired:
                self.log("⚠️ Force killing process...")
                self.voice_process.kill()
                self.voice_process.wait()
                self.log("✋ Voice generation forcefully stopped")
            
            self.is_generating_voice = False
            self._update_button_states()
    
    def _update_button_states(self):
        """Update button enabled/disabled states based on generation status."""
        if self.is_generating:
            self.generate_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.NORMAL)
            self.generate_voice_button.config(state=tk.DISABLED)
            self.cancel_voice_button.config(state=tk.DISABLED)
        elif self.is_generating_voice:
            self.generate_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            self.generate_voice_button.config(state=tk.DISABLED)
            self.cancel_voice_button.config(state=tk.NORMAL)
        else:
            self.generate_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            self.generate_voice_button.config(state=tk.NORMAL)
            self.cancel_voice_button.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Handle window close event - stop generation if running."""
        if self.is_generating or self.is_generating_voice:
            if messagebox.askyesno("Confirm", "A process is running. Kill it and exit?"):
                if self.is_generating:
                    self.cancel_generation()
                if self.is_generating_voice:
                    self.cancel_voice_generation()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def extract_narration(self):
        """Extract narration from video package."""
        output_dir = self.output_var.get().strip()
        video_package_path = os.path.join(output_dir, "video_package.json")
        
        if not os.path.exists(video_package_path):
            messagebox.showerror("Error", f"video_package.json not found in {output_dir}\n\nPlease generate a video package first.")
            return
        
        thread = threading.Thread(target=self._extract_narration_thread, args=(video_package_path, output_dir))
        thread.daemon = True
        thread.start()
    
    def _extract_narration_thread(self, video_package_path, output_dir):
        """Run narration extraction in background thread."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        try:
            self.log("=" * 70)
            self.log("📝 Extracting Narration")
            self.log("=" * 70)
            self.log("")
            self.log(f"Video Package: {video_package_path}")
            self.log(f"Output Dir: {output_dir}")
            self.log("")
            self.log("-" * 70)
            
            # Build command
            cmd = [
                "python",
                "extract_narration.py",
                "--video-package", video_package_path,
                "--output", os.path.join(output_dir, "narration_draft.txt")
            ]
            
            self.log("Running command:")
            self.log(" ".join(cmd))
            self.log("")
            
            # Run command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output
            for line in process.stdout:
                self.log(line.rstrip())
            
            process.wait()
            
            if process.returncode == 0:
                self.log("-" * 70)
                self.log("")
                self.log("✅ Narration extraction completed successfully!")
                self.log("")
                self.log("Generated files:")
                narration_file = os.path.join(output_dir, "narration_draft.txt")
                youtube_file = os.path.join(output_dir, "narration_draft_youtube.txt")
                
                if os.path.exists(narration_file):
                    self.log(f"  • narration_draft.txt ({os.path.getsize(narration_file)} bytes)")
                if os.path.exists(youtube_file):
                    self.log(f"  • narration_draft_youtube.txt ({os.path.getsize(youtube_file)} bytes)")
                
                self.log("")
                self.log("✨ Ready for TTS:")
                self.log(f"Use narration_draft_youtube.txt with Gemini TTS")
            else:
                self.log("-" * 70)
                self.log("")
                self.log(f"❌ Extraction failed with exit code {process.returncode}")
        
        except Exception as e:
            self.log("")
            self.log("❌ Error:")
            self.log(str(e))
            messagebox.showerror("Error", str(e))
    
    def generate_voice(self):
        """Generate voice over from narration."""
        output_dir = self.output_var.get().strip()
        narration_file = os.path.join(output_dir, "narration_draft_youtube.txt")
        
        if not os.path.exists(narration_file):
            messagebox.showerror("Error", f"narration_draft_youtube.txt not found in {output_dir}\n\nPlease extract narration first.")
            return
        
        thread = threading.Thread(target=self._generate_voice_thread, args=(narration_file,))
        thread.daemon = True
        thread.start()
    
    def _generate_voice_thread(self, narration_file):
        """Run voice generation in background thread."""
        self.is_generating_voice = True
        self._update_button_states()
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        try:
            self.log("=" * 70)
            self.log("🎙️ Generating Voice Over")
            self.log("=" * 70)
            self.log("")
            
            voice = self.voice_var.get()
            speed = self.speed_var.get()
            voice_output_dir = self.voice_output_var.get().strip()
            
            self.log(f"Narration File: {narration_file}")
            self.log(f"Voice: {voice}")
            self.log(f"Speed: {speed}")
            self.log(f"Output Dir: {voice_output_dir}")
            self.log("")
            self.log("-" * 70)
            
            # Build command
            cmd = [
                "python",
                "voice_generator.py",
                "--narration", narration_file,
                "--output-dir", voice_output_dir,
                "--voice", voice,
                "--speed", str(speed)
            ]
            
            self.log("Running command:")
            self.log(" ".join(cmd))
            self.log("")
            
            # Run command
            self.voice_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output
            for line in self.voice_process.stdout:
                if not self.is_generating_voice:  # Check if cancelled
                    break
                self.log(line.rstrip())
            
            self.voice_process.wait()
            
            if not self.is_generating_voice:
                # User cancelled
                self.log("-" * 70)
                self.log("")
                self.log("⚠️ Voice generation was cancelled")
                return
            
            if self.voice_process.returncode == 0:
                self.log("-" * 70)
                self.log("")
                self.log("✅ Voice generation completed successfully!")
                self.log("")
                self.log("Generated files:")
                self.log(f"  📁 Output directory: {voice_output_dir}")
                
                # List MP3 files
                if os.path.exists(voice_output_dir):
                    mp3_files = [f for f in os.listdir(voice_output_dir) if f.endswith('.mp3')]
                    self.log(f"  📦 Total audio files: {len(mp3_files)}")
                
                self.log("")
                self.log("✨ Next steps:")
                self.log(f"1. Audio files are ready in: {voice_output_dir}")
                self.log("2. Use these MP3 files for your video editing software")
                self.log("3. Combine with video content and background music")
            else:
                self.log("-" * 70)
                self.log("")
                self.log(f"❌ Voice generation failed with exit code {self.voice_process.returncode}")
        
        except Exception as e:
            self.log("")
            self.log("❌ Error:")
            self.log(str(e))
            messagebox.showerror("Error", str(e))
        
        finally:
            self.is_generating_voice = False
            self.voice_process = None
            self._update_button_states()
    
    def generate(self):
        """Generate video package in separate thread."""
        thread = threading.Thread(target=self._generate_thread)
        thread.daemon = True
        thread.start()
    
    def _generate_thread(self):
        """Run generation in background thread."""
        self.is_generating = True
        self._update_button_states()
        
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        try:
            self.log("=" * 70)
            self.log("🎬 Starting Video Generation Pipeline")
            self.log("=" * 70)
            self.log("")
            
            # Validate inputs
            topic = self.topic_var.get().strip()
            length_seconds = self.length_var.get()
            scenes_count = self.scenes_var.get()
            retrieval_limit = self.retrieval_var.get()
            enable_reasoning = self.reasoning_var.get()
            retrieved_docs = self.docs_var.get().strip()
            output_dir = self.output_var.get().strip()
            
            if not topic:
                raise ValueError("Topic cannot be empty")
            if length_seconds < 15:
                raise ValueError("Duration must be at least 15 seconds")
            if scenes_count < 2:
                raise ValueError("Must have at least 2 scenes")
            
            self.log(f"Topic: {topic}")
            self.log(f"Duration: {length_seconds}s")
            self.log(f"Scenes: {scenes_count}")
            self.log(f"Retrieval Limit: {retrieval_limit}")
            self.log(f"Enable Reasoning: {enable_reasoning}")
            if retrieved_docs:
                self.log(f"Retrieved Docs: {retrieved_docs}")
            self.log(f"Output Dir: {output_dir}")
            self.log("")
            
            # Build command
            cmd = [
                "python",
                "generate_video_package.py",
                "--topic", topic,
                "--length-seconds", str(length_seconds),
                "--scenes-count", str(scenes_count),
                "--retrieval-limit", str(retrieval_limit),
                "--output-dir", output_dir
            ]
            
            if enable_reasoning:
                cmd.append("--enable-reasoning")
            
            if retrieved_docs and os.path.exists(retrieved_docs):
                cmd.extend(["--retrieved-docs", retrieved_docs])
            
            self.log("Running command:")
            self.log(" ".join(cmd))
            self.log("")
            self.log("-" * 70)
            
            # Run command
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output
            for line in self.current_process.stdout:
                if not self.is_generating:  # Check if cancelled
                    break
                self.log(line.rstrip())
            
            self.current_process.wait()
            
            if not self.is_generating:
                # User cancelled
                self.log("-" * 70)
                self.log("")
                self.log("⚠️ Generation was cancelled")
                return
            
            if self.current_process.returncode == 0:
                self.log("-" * 70)
                self.log("")
                self.log("✅ Generation completed successfully!")
                self.log("")
                
                # List output files
                output_path = Path(output_dir)
                if output_path.exists():
                    self.log("Generated files:")
                    for file in sorted(output_path.glob("*.json")):
                        self.log(f"  • {file.name}")
                    for file in sorted(output_path.glob("*.txt")):
                        self.log(f"  • {file.name}")
                
                self.log("")
                self.log("📊 Next steps:")
                self.log("1. Run: python extract_narration.py --video-package " + str(output_path / "video_package.json"))
                self.log("2. This generates narration_draft.txt and narration_draft_youtube.txt")
                self.log("3. Use narration_draft_youtube.txt with Gemini TTS")
                
            else:
                self.log("-" * 70)
                self.log("")
                self.log(f"❌ Generation failed with exit code {self.current_process.returncode}")
        
        except Exception as e:
            self.log("")
            self.log("❌ Error:")
            self.log(str(e))
            messagebox.showerror("Error", str(e))
        
        finally:
            self.is_generating = False
            self.current_process = None
            self._update_button_states()


def main():
    root = tk.Tk()
    app = VideoGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
