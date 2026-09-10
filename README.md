# transcribe

Often when I'm working on a story, I'll record 5 or more Zoom interviews. These .m4a recordings sit in a folder on my desktop collecting dust, reminding me I need to organize my notes, find relevant quotes, and start writing. I used to pay for Otter (80 bucks a year as a freelance journalist, egad!) and then I used a wonderful service called Scroll that was free for journalists. Until it shut down, womp womp. So I decided to build my own tool that relies on OpenAI's Whisper and spits out quick transcripts for free, when I'm under deadline.

What I especially like about it is that everything runs locally. You don't have to upload files anywhere — recordings and transcripts all live on your computer.

Depending on whether interviews are sensitive or not, I then take my transcribed .txt files and upload them to a project in Claude with strict instructions to only answer questions based on verbatim information pulled from my interviews. That creates a searchable, queryable corpus of interviews, which I find immensely useful for information-dense and multiple-interview drafts. More info on that in the LLM section.

Of course, there are plenty of other transcription tools out there that are far more sophisticated than this one. My aim is to share tools and tricks that simplify my workflow and let me focus on the fun part of journalism: writing and reporting.

## What it does

Point the script at a folder of recordings — either by running it from inside that folder, or with `--dir /path/to/folder`. For each audio file it finds, it runs three steps:

1. Converts `name.m4a` to `name.wav` (16 kHz, mono — the format Whisper expects) with **ffmpeg**, a free audio-conversion tool
2. Transcribes it with **whisper-cli** (a local version of OpenAI's Whisper speech-to-text model), producing `name.wav.srt`
3. Rewrites that into a clean, readable `name_timestamps.txt`

Every step is skipped if its output already exists, so re-running after an interruption picks up where it left off rather than starting over.

## Requirements

The script itself doesn't transcribe anything — it hands your audio off to ffmpeg and whisper-cli, the two free tools mentioned above. You install those once, and this script just drives them for you.

Everything in this section happens in **Terminal** — open it from Applications → Utilities → Terminal, or press `⌘ Space` and type "Terminal."

- Python 3.8+ — check with `python3 --version`; if it's missing, macOS will prompt you to install it (nothing extra to `pip install` either way)
- **ffmpeg**
- **whisper-cli**, with a model file at `~/.whisper-cpp/models/ggml-small.bin`

ffmpeg and whisper-cpp install through **Homebrew**, a free package manager for command-line tools. If you don't already have Homebrew, install it first — paste this into Terminal, press Return, and follow the prompts (it'll ask for your Mac password):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install ffmpeg and whisper-cpp:

```bash
brew install ffmpeg whisper-cpp
```

Then download a model:

```bash
mkdir -p ~/.whisper-cpp/models
curl -L -o ~/.whisper-cpp/models/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
```

`small` is a reasonable speed/accuracy tradeoff for interview audio. `ggml-medium.bin` is more accurate and noticeably slower — download it the same way and point at it with `--model`, or set `WHISPER_MODEL` in your shell config file if you always want it.

## Install

**If you don't use git** (the easiest path for most people):

1. Click the green **Code** button near the top of this page, then **Download ZIP**.
2. Find the downloaded file — usually in your **Downloads** folder — and double-click it to unzip. This creates a folder called `transcribe-main`.
3. Open Terminal.
4. Move into that folder — if it's in Downloads, this is:

   ```bash
   cd ~/Downloads/transcribe-main
   ```

   (If you dragged the folder somewhere else first, like the Desktop, use that path instead — e.g. `cd ~/Desktop/transcribe-main`.)

**If you use git instead:**

```bash
git clone https://github.com/joshdaxelrod/transcribe.git
cd transcribe
```

**From here, both paths continue the same way.** Teach your terminal a shortcut so you can type `transcribe` instead of the full path to the script every time. This adds one line to your shell's config file (a plain text file your terminal reads every time it opens):

```bash
echo "alias transcribe='python3 $PWD/transcribe.py'" >> ~/.zshrc
```

(This is for zsh, the default on modern macOS. Using bash? Use `~/.bashrc` or `~/.bash_profile` instead of `~/.zshrc`.)

Close and reopen your Terminal window so the change takes effect (or run `source ~/.zshrc` in the same window).

To check it worked:

```bash
transcribe --help
```

If you see a list of options, you're set up.

## Usage

With the alias set up (see Install), the everyday version is just:

```bash
cd ~/Desktop/interviews
transcribe
```

`cd` ("change directory") tells Terminal which folder to work in. `~/Desktop/interviews` means the folder called `interviews` on your Desktop — if your recordings live in a folder with a different name, type that name instead (e.g. `cd ~/Desktop/carbon-capture`). If the folder isn't on your Desktop, replace `Desktop` with wherever it actually is.

Once you're standing in that folder, `transcribe` processes every `.m4a` and `.wav` file it finds there.

**Single file** — give the basename, without the extension:

```bash
transcribe gerald
```

That looks for `gerald.m4a` (or `gerald.wav` if the conversion already happened) and writes `gerald_timestamps.txt` alongside it.

**No alias set up yet, or pointing at a folder you're not standing in?** Call the script directly by its full path, and pass `--dir` for the recordings:

```bash
python3 /path/to/transcribe.py --dir ~/Desktop/interviews
python3 /path/to/transcribe.py gerald --dir ~/Desktop/interviews
```

(`/path/to/transcribe.py` is wherever you cloned or unzipped this repo — e.g. `~/transcribe/transcribe.py`.)

### Options

| Flag | Default | Notes |
|---|---|---|
| `--dir` | current directory | Where the audio lives |
| `--language` | `en` | Any Whisper language code (`de`, `fr`, `es`…). Use `auto` to let Whisper detect it, which is slightly slower and occasionally guesses wrong on short or noisy clips. |
| `--model` | `~/.whisper-cpp/models/ggml-small.bin` | Also settable via the `WHISPER_MODEL` environment variable |

```bash
transcribe --language de --model ~/.whisper-cpp/models/ggml-medium.bin
```

## Output

For an input `gerald.m4a`, you end up with:

| File | What it is |
|---|---|
| `gerald.wav` | 16 kHz mono intermediate — safe to delete afterwards |
| `gerald.wav.srt` | Subtitle file from whisper, useful if you want to burn captions into video |
| `gerald_timestamps.txt` | The one you actually want |

In batch mode, a failure on one file doesn't stop the run. Everything else is attempted, and a summary at the end lists what succeeded and what didn't.

## LLM

Once you have a folder of transcripts, you can upload these text files to a project on an LLM. I then like to query that project as I'm drafting.

My workflow:

1. Create a new Project in Claude (any LLM with a "project" or "custom instructions + file upload" feature works — ChatGPT has an equivalent).
2. Upload the `_timestamps.txt` files for a story into the project's knowledge base.
3. Set project instructions along these lines:

> You are a quote-retrieval tool. Your sole purpose is to surface content from the interview/source transcripts (and any accompanying notes) stored in this project. You are not a general-knowledge assistant, editorial partner, or outliner.
>
> **Scope** — Do not answer general questions, search the web, or supply outside facts, context, or explanation. Do not offer story angles, structure suggestions, or thematic analysis — grouping quotes by theme for readability (see Retrieval behavior) is a formatting choice, not analysis, and is fine by default; interpreting what the themes mean is not. If asked something unrelated to the transcripts, redirect: say you only work with the uploaded transcripts and ask what topic or phrase to search for.
>
> **Quote formatting** — Always pull quotes verbatim from the transcript. Never paraphrase, summarize, or condense actual content, even long or rambling answers — this includes no smoothing syntax and no cutting repetition that's part of the actual content. You may lightly clean two things only: filler words/verbal tics (e.g. "um," "you know") and obvious transcription errors (e.g. a misheard homonym or garbled term you can confidently correct). If you're unsure whether something is a filler tic or substantive, leave it in. Include the transcript filename and timestamp with every quote. If no exact quote exists on a topic, say so directly rather than reaching or approximating. If a source addresses the topic in multiple, non-contiguous places in the same transcript, return each as a separate quote block with its own timestamp — never merge non-contiguous passages into one quote.
>
> **Retrieval behavior** — Default mode: when asked for quotes/content on a topic or phrase, search all transcripts and return every relevant passage, grouped by theme so the reporter can see how different sources address the same topic side by side. Do not apply editorial judgment about which quotes are "best" or "most powerful" unless explicitly asked — default behavior is comprehensive retrieval, not curation. Do not editorialize about completeness (e.g. "I found X quotes, though there may be more") unless asked.
4. Then ask it things like "What did any source say about X?", "Pull every quote about Y, with timestamps," or "Which interviews mention Z?"

That turns hours of scrubbing through recordings into a few seconds of search, while keeping the actual writing and editorial judgment with me.

Of course, some important caveats apply:

- **Verify everything against the source audio.** Even with strict instructions, LLMs can still misquote or drop context. The timestamp exists so you can check before it goes in a draft.
- **Think about sensitivity before you upload anything.** Not everything should go in an LLM. Be thoughtful about what you're uploading. When in doubt, don't upload it — work from the local `.txt` file instead.
- **Check your provider's data-training settings** before uploading anything sensitive. Claude and ChatGPT both offer accounts/tiers where your data isn't used for training — confirm that's actually configured before you rely on it.

## Limitations

**No speaker labels.** This is the big one for interview work. Whisper transcribes what was said, not who said it — so a two-person interview comes out as one undifferentiated stream of text, and you'll be marking up turns by hand. Separating speakers (diarization) needs a second model on top of Whisper; [WhisperX](https://github.com/m-bain/whisperX) is the usual route if you need it, at the cost of a much heavier install.

**Transcription is a first draft.** Expect errors on proper nouns, crosstalk, technical vocabulary, and anyone speaking away from the microphone. Timestamps exist so you can jump back to the audio and check — treat the text as an index into the recording, not a replacement for it.

**One language per run.** The `--language` flag applies to every file in a batch. Code-switching within an interview, or a folder mixing languages, will need separate runs.

## License

MIT — see [LICENSE](LICENSE).

Built with AI assistance (Claude), reviewed and tested by me.

## About

Written by [Josh Axelrod](https://josh-axelrod.com), an investigative reporter and 2023–24 Fulbright Journalism Fellow based in Berlin, Germany. He covers extremism, disinformation, and technology; his work has appeared in WIRED, Mother Jones, Deutsche Welle, Die Zeit, The Daily Beast, NPR, and more.
