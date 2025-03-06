from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, CHAP, CTOC, TDRL
import argparse
from datetime import datetime

def remove_chapters_from_mp3(input_file, output_file, filter_string):
    """
    Removes chapters from an MP3 file based on a filter string in the chapter title.
    """
    try:
        # Load audio file and ID3 tags
        audio = MP3(input_file, ID3=ID3)
        id3 = ID3(input_file)
        print(f"Loaded ID3 tags from {input_file}")
        
        # Collect chapters and TOC
        chapters_to_remove = []
        all_chapters = []
        toc_element = None
        
        # Extract chapter information
        for key, frame in id3.items():
            if isinstance(frame, CHAP):
                title = ""
                if frame.sub_frames:
                    for sub_key, sub_frame in frame.sub_frames.items():
                        if sub_key.startswith('TIT2'):
                            title = str(sub_frame)
                            break
                all_chapters.append((frame.element_id, frame, title, frame.start_time, frame.end_time))
            elif isinstance(frame, CTOC):
                toc_element = frame
        
        # Sort chapters by start time
        all_chapters.sort(key=lambda x: x[3])
        
        # Identify chapters to remove and calculate time adjustments
        total_time_adjustment = 0
        chapters_time_adjustments = []
        
        for element_id, frame, title, start_time, end_time in all_chapters:
            if filter_string.lower() in title.lower():
                print(f"Removing chapter: '{title}'")
                chapters_to_remove.append(element_id)
                total_time_adjustment += (end_time - start_time)
            
            chapters_time_adjustments.append(total_time_adjustment)
        
        print(f"Found {len(chapters_to_remove)} chapters to remove")
        
        # Update timing of remaining chapters
        for i, (element_id, frame, title, start_time, end_time) in enumerate(all_chapters):
            if element_id not in chapters_to_remove:
                adjustment = chapters_time_adjustments[i]
                frame.start_time -= adjustment
                frame.end_time -= adjustment
        
        # Load and process audio
        audio_segment = AudioSegment.from_mp3(input_file)
        new_audio_segment = AudioSegment.empty()
        
        # Build new audio from remaining chapters
        chapter_count = 0
        for i, (element_id, frame, title, start_time, end_time) in enumerate(all_chapters):
            if element_id not in chapters_to_remove:
                chapter_count += 1
                frame.element_id = f'ch{chapter_count}'  # Renumber chapters sequentially
                chapter_segment = audio_segment[start_time:end_time]
                new_audio_segment += chapter_segment
        
        # Export new audio
        print(f"Exporting new audio ({len(new_audio_segment)/1000:.2f}s) to {output_file}")
        new_audio_segment.export(output_file, format="mp3")
        
        # Update ID3 tags
        output_id3 = ID3(output_file)
        
        # Create new TOC with sequential chapter IDs
        new_toc_element = CTOC(
            element_id=toc_element.element_id if toc_element else "toc",
            flags=toc_element.flags if toc_element else 3,
            child_element_ids=[f'ch{i+1}' for i in range(chapter_count)]
        )
        output_id3.add(new_toc_element)

        # Add remaining chapters to the new ID3 tags
        for element_id, frame, title, start_time, end_time in all_chapters:
            if element_id not in chapters_to_remove:
                output_id3.add(frame)
        
        # Copy remaining tags
        for key, frame in id3.items():
            if not isinstance(frame, CTOC) and not isinstance(frame, CHAP):
                output_id3.add(frame)
        
        # Add publication date
        output_id3.add(TDRL(encoding=3, text=datetime.now().strftime("%Y-%m-%d")))
        
        # Save tags
        output_id3.save()
        print("Successfully processed file")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Remove chapters from an MP3 file based on a filter string.")
    parser.add_argument("--input_file", required=True, help="Path to the input MP3 file.")
    parser.add_argument("--output_file", required=True, help="Path to the output MP3 file.")
    parser.add_argument("--filter_string", required=True, help="String to filter chapters to be removed.")

    args = parser.parse_args()
    
    print(f"Processing: {args.input_file} → {args.output_file} (filter: '{args.filter_string}')")
    remove_chapters_from_mp3(args.input_file, args.output_file, args.filter_string)
    print(f"Successfully created {args.output_file}")