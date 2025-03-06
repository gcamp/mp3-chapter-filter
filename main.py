from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, CHAP, CTOC, TDRL
import io
import argparse
from datetime import datetime

def remove_chapters_from_mp3(input_file, output_file, filter_string):
    """
    Removes chapters from an MP3 file based on a filter string in the chapter title.

    Args:
        input_file (str): Path to the input MP3 file.
        output_file (str): Path to the output MP3 file.
        filter_string (str): String to filter chapters to be removed.
    """
    print("Opening MP3 file")
    audio = MP3(input_file, ID3=ID3)
    
    print(f"Opening id3 file: {input_file}")
    id3 = ID3(input_file)
    print(f"Successfully loaded ID3 tags from {input_file}")
    
    # Get chapter information
    print(f"Scanning for chapters with filter string: '{filter_string}'")
    chapters_to_remove = []
    toc_element = None
    all_chapters = []
    chapters_time_adjustments = []
    total_time_adjustment = 0
    
    # First, collect all chapters
    for key, frame in id3.items():
        if isinstance(frame, CHAP):
            # Extract the actual chapter title from the chapter's subframes
            title = ""
            if frame.sub_frames:
                for sub_key, sub_frame in frame.sub_frames.items():
                    if sub_key.startswith('TIT2'):  # TIT2 contains the title
                        title = str(sub_frame)
                        break
            
            # Store all chapters for later processing
            all_chapters.append((frame.element_id, frame, title, frame.start_time, frame.end_time))
        elif isinstance(frame, CTOC):
            toc_element = frame
    
    # Sort chapters by start time
    all_chapters.sort(key=lambda x: x[3])
    
    # Identify chapters to remove and calculate time adjustments
    for element_id, frame, title, start_time, end_time in all_chapters:
        if filter_string.lower() in title.lower():
            print(f"Removing chapter with title '{title}'")
            chapters_to_remove.append(element_id)
            # Track the time adjustment needed for subsequent chapters
            chapter_duration = end_time - start_time
            total_time_adjustment += chapter_duration
        else:
            print(f"Keeping chapter with title '{title}'")
        
        chapters_time_adjustments.append(total_time_adjustment)
    
    # Sort chapters by start time
    all_chapters.sort(key=lambda x: x[3])
    
    # Update timing of remaining chapters
    for i, (element_id, frame, title, start_time, end_time) in enumerate(all_chapters):
        if element_id not in chapters_to_remove:
            adjustment = chapters_time_adjustments[i]
            frame.start_time -= adjustment
            frame.end_time -= adjustment
            print(f"Updated chapter '{title}': {start_time}ms → {frame.start_time}ms, {end_time}ms → {frame.end_time}ms (adjustment: {adjustment}ms)")

    print(f"Found {len(chapters_to_remove)} chapters to remove")
    
    # Remove unwanted chapters from toc
    if toc_element:
        print(f"Updating table of contents")
        new_child_element_ids = [x for x in toc_element.child_element_ids if x not in chapters_to_remove]
        toc_element.child_element_ids = new_child_element_ids
        print(f"Updated and saved TOC in original file")

    # Load the audio segment
    print(f"Loading audio data from {input_file}")
    audio_segment = AudioSegment.from_mp3(input_file)
    print(f"Successfully loaded audio data: {len(audio_segment)/1000:.2f} seconds")
    
    # Create a new audio segment without the removed chapters
    print("Creating new audio segment without filtered chapters")
    new_audio_segment = AudioSegment.empty()
    
    valid_chapters = []
    for key, frame in id3.items():
        if isinstance(frame, CHAP):
            if frame.element_id not in chapters_to_remove:
                valid_chapters.append(frame)

    print(f"Found {len(valid_chapters)} valid chapters to keep")
    
    # Sort chapters by start time
    valid_chapters.sort(key=lambda x: x.start_time)
    
    print("Processing chapters:")
    for i, chapter in enumerate(valid_chapters):
        start_time = chapter.start_time
        end_time = chapter.end_time
        duration = (end_time - start_time) / 1000  # Convert to seconds
        print(f"  Chapter {i+1}/{len(valid_chapters)}: {start_time}ms to {end_time}ms ({duration:.2f}s)")
        
        chapter_segment = audio_segment[start_time:end_time]
        new_audio_segment += chapter_segment
    
    print(f"New audio duration: {len(new_audio_segment)/1000:.2f} seconds")
    
    # Export the new audio segment to a new MP3 file
    print(f"Exporting new audio to {output_file}")
    new_audio_segment.export(output_file, format="mp3")
    print(f"Audio export complete")
    
    # Copy the ID3 tags to the new file after exporting
    print("Copying ID3 tags to new file")
    output_id3 = ID3(output_file)

    # Make sure we're using the modified TOC that we updated earlier
    if toc_element:
        output_id3.add(toc_element)
        print("Updated table of contents in new file")

    # Copy all ID3 tags from the original file, except the chapters we want to remove
    for key, frame in id3.items():
        if isinstance(frame, CHAP):
            # Only add chapters that aren't in our remove list
            if frame.element_id not in chapters_to_remove:
                # Chapters might need offset correction since we've modified the audio
                output_id3.add(frame)
        elif not isinstance(frame, CTOC):
            # Add all non-chapter tags except table of contents
            output_id3.add(frame)

    print(f"Copied ID3 tags to the new file")

    # Add current date as publication date
    # Format date as YYYY-MM-DD (ID3v2.4 format)
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_id3.add(TDRL(encoding=3, text=current_date))
    print(f"Added publication date: {current_date}")
    
    print("Saving final ID3 tags")
    output_id3.save()
    print("ID3 tags saved successfully")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Remove chapters from an MP3 file based on a filter string.")
    parser.add_argument("--input_file", required=True, help="Path to the input MP3 file.")
    parser.add_argument("--output_file", required=True, help="Path to the output MP3 file.")
    parser.add_argument("--filter_string", required=True, help="String to filter chapters to be removed.")

    args = parser.parse_args()

    input_mp3_file = args.input_file
    output_mp3_file = args.output_file
    filter_string = args.filter_string
    print(f"Filtering chapters, input MP3 file: {input_mp3_file}, Output MP3 file: {output_mp3_file}, Filter string: {filter_string}")

    remove_chapters_from_mp3(input_mp3_file, output_mp3_file, filter_string)
    print(f"Successfully created {output_mp3_file} with chapters containing '{filter_string}' removed.")