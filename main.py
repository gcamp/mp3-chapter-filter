from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, CHAP, CTOC
import io
import argparse
from datetime import datetime
from mutagen.id3 import TDRL

def remove_chapters_from_mp3(input_file, output_file, filter_string):
    """
    Removes chapters from an MP3 file based on a filter string in the chapter title.

    Args:
        input_file (str): Path to the input MP3 file.
        output_file (str): Path to the output MP3 file.
        filter_string (str): String to filter chapters to be removed.
    """

    audio = MP3(input_file, ID3=ID3)
    id3 = ID3(input_file)

    # Get chapter information
    chapters_to_remove = []
    toc_element = None
    for key, frame in id3.items():
        if isinstance(frame, CHAP):
            # Extract the actual chapter title from the chapter's subframes
            title = ""
            if frame.sub_frames:
                for sub_key, sub_frame in frame.sub_frames.items():
                    if sub_key.startswith('TIT2'):  # TIT2 contains the title
                        title = str(sub_frame)
                        break
            
            if filter_string.lower() in title.lower():
                print(f"Removing chapter with title '{title}'")
                chapters_to_remove.append(frame.element_id)
        elif isinstance(frame, CTOC):
            toc_element = frame

    # Remove unwanted chapters from toc
    if toc_element:
        new_child_element_ids = [x for x in toc_element.child_element_ids if x not in chapters_to_remove]
        toc_element.child_element_ids = new_child_element_ids
        id3.save()

    # Load the audio segment
    audio_segment = AudioSegment.from_mp3(input_file)
    
    # Create a new audio segment without the removed chapters
    new_audio_segment = AudioSegment.empty()
    
    
    valid_chapters = []
    for key, frame in id3.items():
        if isinstance(frame, CHAP):
            if frame.element_id not in chapters_to_remove:
                valid_chapters.append(frame)

    # Sort chapters by start time
    valid_chapters.sort(key=lambda x: x.start_time)

    for i, chapter in enumerate(valid_chapters):
        start_time = chapter.start_time
        end_time = chapter.end_time
            
        chapter_segment = audio_segment[start_time:end_time]
        new_audio_segment += chapter_segment
    
    # Export the new audio segment to a new MP3 file
    new_audio_segment.export(output_file, format="mp3")
    
    # Copy the ID3 tags to the new file after exporting
    output_id3 = ID3(output_file)
    # Copy all ID3 tags from the original file, except the chapters we want to remove
    for key, frame in id3.items():
        if not isinstance(frame, CHAP) or frame.element_id not in chapters_to_remove:
            output_id3.add(frame)
    
    # Make sure we're using the modified TOC that we updated earlier
    if toc_element and toc_element.element_id in id3:
        output_id3.add(id3[toc_element.element_id])

    # Add current date as publication date
    # Format date as YYYY-MM-DD (ID3v2.4 format)
    current_date = datetime.now().strftime("%Y-%m-%d")
    output_id3.add(TDRL(encoding=3, text=current_date))
    
    output_id3.save()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Remove chapters from an MP3 file based on a filter string.")
    parser.add_argument("--input_file", required=True, help="Path to the input MP3 file.")
    parser.add_argument("--output_file", required=True, help="Path to the output MP3 file.")
    parser.add_argument("--filter_string", required=True, help="String to filter chapters to be removed.")

    args = parser.parse_args()

    input_mp3_file = args.input_file
    output_mp3_file = args.output_file
    filter_string = args.filter_string

    remove_chapters_from_mp3(input_mp3_file, output_mp3_file, filter_string)
    print(f"Successfully created {output_mp3_file} with chapters containing '{filter_string}' removed.")