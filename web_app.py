"""
web_app.py
----------
Small web interface for the dubbing system (built with Gradio).

The user only supplies a YouTube URL (or uploads a video). The app then:

  Step 1  downloads the video and finds a few clean samples of the
          original speaker's voice - the user listens and picks one
          (or uploads their own sample).
  Step 2  one button: the speech is transcribed, translated and spoken
          in a clone of that voice, and the dubbed video appears.

Run locally:        python web_app.py
Run from Colab:     see Colab_notebook/Dubbing_Pipeline_Colab.ipynb
                    (share=True gives a public link served by that
                    Colab session's GPU while the session stays open).

Note: one job at a time - intermediate files live in data/.
"""

import gradio as gr

from app import dub_video, find_reference_voices, prepare_source
from src.logger import log_error

SAMPLE_COUNT = 3


def _fail(message: str):
    log_error(message)
    raise gr.Error(message)


def find_voice(url, uploaded_video):
    """Step 1: download, extract audio, cut candidate voice samples."""

    url = (url or "").strip()

    if not url and not uploaded_video:
        _fail("Paste a YouTube URL or upload a video first.")

    try:
        video, audio = prepare_source(url or None, uploaded_video or None)
        candidates = find_reference_voices(video, audio, top_n=SAMPLE_COUNT)
    except Exception as e:
        _fail(f"Could not prepare the video: {e}")

    labels = [f"Sample {i}" for i in range(1, len(candidates) + 1)]

    state = {"video": video, "audio": audio, "candidates": candidates}

    return (
        state,
        gr.update(choices=labels, value=labels[0]),
        candidates[0],
        gr.update(visible=True),
        "Listen to the sample. If it sounds like the speaker, press "
        "'Use this voice'. Otherwise pick another sample or upload your own.",
    )


def choose_sample(choice, state):
    """Switch the player to the sample the user selected."""

    if not state or not choice:
        return None

    index = int(choice.split()[-1]) - 1
    return state["candidates"][index]


def make_dub(state, own_sample, choice):
    """Step 2: dub the video using the approved voice."""

    if not state:
        _fail("Run step 1 first.")

    if own_sample:
        reference = own_sample
    else:
        index = int(choice.split()[-1]) - 1
        reference = state["candidates"][index]

    try:
        final_video, language = dub_video(
            state["video"],
            state["audio"],
            tts_backend="chatterbox",
            reference_voice=reference,
            resume=False,
        )
    except Exception as e:
        _fail(f"Dubbing failed: {e}")

    return final_video, f"Done. Detected language: {language}."


def build_ui():
    with gr.Blocks(title="YouTube Video Dubbing") as demo:
        gr.Markdown(
            "# YouTube Video Dubbing\n"
            "Dub a video into English **in the original speaker's voice**."
        )

        state = gr.State()

        gr.Markdown("### Step 1 - Video")
        url = gr.Textbox(label="YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        upload = gr.Video(label="...or upload a video file (use this if YouTube blocks the download)")
        find_btn = gr.Button("1. Find the speaker's voice", variant="primary")
        status = gr.Textbox(label="Status", interactive=False)

        with gr.Column(visible=False) as step2:
            gr.Markdown("### Step 2 - Confirm the voice")
            choice = gr.Radio(label="Voice sample", choices=[])
            player = gr.Audio(label="Does this sound like the speaker?", type="filepath")
            own = gr.Audio(
                label="Not right? Upload your own voice sample instead (optional, 10-20 s of clean speech)",
                type="filepath",
                sources=["upload"],
            )
            dub_btn = gr.Button("2. Use this voice and create the dubbed video", variant="primary")
            result = gr.Video(label="Dubbed video")
            result_status = gr.Textbox(label="Result", interactive=False)

        find_btn.click(
            find_voice,
            inputs=[url, upload],
            outputs=[state, choice, player, step2, status],
        )
        choice.change(choose_sample, inputs=[choice, state], outputs=player)
        dub_btn.click(
            make_dub,
            inputs=[state, own, choice],
            outputs=[result, result_status],
        )

    return demo


if __name__ == "__main__":
    build_ui().queue().launch()
