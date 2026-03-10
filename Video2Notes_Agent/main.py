#!/usr/bin/env python3
"""
VideoNotes - Intelligent Video to Notes Converter
Converts long videos into structured, meaningful notes using AI.
"""

import argparse
import sys
import os
from pathlib import Path
import dotenv
dotenv.load_dotenv()
from extractor import AudioExtractor
from transcriber import WhisperTranscriber
from analyzer import ChunkAnalyzer
from synthesizer import NotesSynthesizer
from config import Config


def print_banner():
    print("""
╔══════════════════════════════════════════╗
║         VideoNotes - AI Notes Agent      ║
║   Turn any video into intelligent notes  ║
╚══════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(
        description="Convert videos into intelligent notes using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --url "https://youtube.com/watch?v=..." 
  python main.py --file lecture.mp4
  python main.py --url "..." --chunk-size 3 --output notes.md
  python main.py --file video.mp4 --model large-v3 --detail high
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", help="YouTube or video URL")
    input_group.add_argument("--file", help="Path to local video/audio file")

    # Output options
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (default: <video_name>_notes.md)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown",
                        help="Output format (default: markdown)")

    # Processing options
    parser.add_argument("--chunk-size", type=int, default=2,
                        help="Minutes per analysis chunk (default: 2)")
    parser.add_argument("--model", default="base",
                        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                        help="Whisper model size (default: base, use large-v3 for best accuracy)")
    parser.add_argument("--detail", choices=["low", "medium", "high"], default="medium",
                        help="Notes detail level (default: medium)")
    parser.add_argument("--language", default=None,
                        help="Video language (default: auto-detect)")

    # Feature flags
    parser.add_argument("--keep-qa", action="store_true",
                        help="Include Q&A sections in notes")
    parser.add_argument("--keep-examples", action="store_true", default=True,
                        help="Include examples and analogies (default: True)")
    parser.add_argument("--timestamps", action="store_true", default=True,
                        help="Include timestamps in notes (default: True)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed processing info")

    args = parser.parse_args()

    print_banner()

    # Build config
    config = Config(
        chunk_size_minutes=args.chunk_size,
        whisper_model=args.model,
        detail_level=args.detail,
        language=args.language,
        keep_qa=args.keep_qa,
        keep_examples=args.keep_examples,
        include_timestamps=args.timestamps,
        verbose=args.verbose,
        output_format=args.format,
    )

    # Check for Anthropic API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set.")
        print("   Please set it in your environment or add it to a .env file:")
        print("   ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    try:
        # Step 1: Extract audio
        print("📥 Step 1/4: Extracting audio...")
        extractor = AudioExtractor(config)
        audio_path, video_title, video_description = extractor.extract(
            url=args.url, file_path=args.file
        )
        print(f"   ✓ Audio ready: {video_title}")

        # Step 2: Transcribe
        print(f"\n🎤 Step 2/4: Transcribing with Whisper ({args.model})...")
        transcriber = WhisperTranscriber(config)
        chunks = transcriber.transcribe(audio_path)
        total_duration = chunks[-1].end_time if chunks else 0
        print(f"   ✓ Transcribed {len(chunks)} chunks ({total_duration/60:.1f} min total)")

        # Step 3: Analyze chunks intelligently
        print(f"\n🧠 Step 3/4: Analyzing {len(chunks)} chunks with AI...")
        analyzer = ChunkAnalyzer(config)
        analyzed_chunks = analyzer.analyze_all(chunks, video_title, video_description)

        core_count = sum(1 for c in analyzed_chunks if c.classification == "CORE")
        pruned_count = len(analyzed_chunks) - core_count
        print(f"   ✓ {core_count} core chunks kept, {pruned_count} pruned (intros/jokes/filler)")

        # Step 4: Synthesize notes
        print(f"\n📝 Step 4/4: Synthesizing final notes...")
        synthesizer = NotesSynthesizer(config)
        notes = synthesizer.synthesize(analyzed_chunks, video_title, total_duration)

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in video_title)
            safe_title = safe_title[:50].strip()
            ext = ".md" if args.format == "markdown" else ".json"
            output_path = Path(f"{safe_title}_notes{ext}")

        # Write output
        output_path.write_text(notes, encoding="utf-8")
        print(f"\n✅ Notes saved to: {output_path}")

        # Print quick stats
        lines = notes.count("\n")
        words = len(notes.split())
        orig_words = sum(len(c.text.split()) for c in chunks)
        compression = (1 - words / orig_words) * 100 if orig_words > 0 else 0
        print(f"   📊 {words:,} words | {lines} lines | {compression:.0f}% compression")

        # Cleanup temp audio
        extractor.cleanup()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
