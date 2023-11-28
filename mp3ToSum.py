# import evadb
import os
import time
from time import perf_counter

import sys

# from gpt4all import GPT4All
# from unidecode import unidecode
from util import download_story, read_text_line
import speech_recognition as sr
from pydub import AudioSegment
AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"
AudioSegment.ffprobe = "/opt/homebrew/bin/ffprobe"
MAX_CHUNK_SIZE = 10000

APP_SOURCE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_VIDEO_PATH = os.path.join(
    APP_SOURCE_DIR, "benchmarks", "testPodcast.mp3")
# temporary file paths
TRANSCRIPT_PATH = os.path.join("evadb_data", "tmp", "transcript.txt")


def transcribe_sphinx(audio_path):
    r = sr.Recognizer()

    # Convert mp3 file to wav for compatibility with SpeechRecognition
    print("1")
    sound = AudioSegment.from_mp3(audio_path)
    print("2")
    audio_path_wav = "temporary_wav_file.wav"
    print("3")
    sound.export(audio_path_wav, format="wav")
    print("4")

    with sr.AudioFile(audio_path_wav) as source:
        audio_data = r.record(source)
        text = r.recognize_sphinx(audio_data)
    print("5")
    return text


def receive_user_input():
    """Receives user input.

    Returns:
        user_input (dict): global configurations
    """
    print(
        "🔮 Welcome to EvaDB! This app lets you ask summarize any local MP3 file.\n You will only need to supply file path to the app.\n"
    )
    video_local_path = str(
        input(
            "💽 Enter the local path to your MP3 (press Enter to use the demo MP3): "
        )
    )
    if video_local_path == "":
        video_local_path = DEFAULT_VIDEO_PATH
    start_time = time.time()
    transcript = transcribe_sphinx(video_local_path)
    end_time = time.time()
    time_taken = end_time - start_time
    print(f"Transcription time: {time_taken} seconds")

    print("starting write")
    with open(TRANSCRIPT_PATH, "w") as f:
        f.write(transcript)
    ask_question(TRANSCRIPT_PATH)


def ask_question(story_path: str):
    # Initialize early to exclude download time.
    llm = GPT4All("ggml-model-gpt4all-falcon-q4_0.bin")

    path = os.path.dirname(os.getcwd())
    cursor = evadb.connect().cursor()

    story_table = "TablePPText"
    story_feat_table = "FeatTablePPText"
    index_table = "IndexTable"

    timestamps = {}
    t_i = 0

    timestamps[t_i] = perf_counter()
    print("Setup Function")

    Text_feat_function_query = f"""CREATE UDF IF NOT EXISTS SentenceFeatureExtractor
            IMPL  './sentence_feature_extractor.py';
            """

    cursor.query("DROP UDF IF EXISTS SentenceFeatureExtractor;").execute()
    cursor.query(Text_feat_function_query).execute()

    cursor.query("DROP UDF IF EXISTS Similarity;").execute()
    Similarity_function_query = """CREATE UDF Similarity
                    INPUT (Frame_Array_Open NDARRAY UINT8(3, ANYDIM, ANYDIM),
                           Frame_Array_Base NDARRAY UINT8(3, ANYDIM, ANYDIM),
                           Feature_Extractor_Name TEXT(100))
                    OUTPUT (distance FLOAT(32, 7))
                    TYPE NdarrayFunction
                    IMPL './similarity.py'"""

    cursor.query(Similarity_function_query).execute()

    cursor.query(f"DROP TABLE IF EXISTS {story_table};").execute()
    cursor.query(f"DROP TABLE IF EXISTS {story_feat_table};").execute()

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print("Create table")

    cursor.query(
        f"CREATE TABLE {story_table} (id INTEGER, data TEXT(1000));").execute()

    # Insert text chunk by chunk.
    for i, text in enumerate(read_text_line(story_path)):
        print("text: --" + text + "--")
        ascii_text = unidecode(text)
        cursor.query(
            f"""INSERT INTO {story_table} (id, data)
                VALUES ({i}, '{ascii_text}');"""
        ).execute()

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print("Extract features")

    # Extract features from text.
    cursor.query(
        f"""CREATE TABLE {story_feat_table} AS
        SELECT SentenceFeatureExtractor(data), data FROM {story_table};"""
    ).execute()

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print("Create index")

    # Create search index on extracted features.
    cursor.query(
        f"CREATE INDEX {index_table} ON {story_feat_table} (features) USING QDRANT;"
    ).execute()

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print("Query")

    # Search similar text as the asked question.
    question = "What is a summary of this article?"
    ascii_question = unidecode(question)

    # Instead of passing all the information to the LLM, we extract the 5 topmost similar sentences
    # and use them as context for the LLM to answer.
    res_batch = cursor.query(
        f"""SELECT data FROM {story_feat_table}
        ORDER BY Similarity(SentenceFeatureExtractor('{ascii_question}'),features)
        LIMIT 5;"""
    ).execute()

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print("Merge")

    # Merge all context information.
    context_list = []
    for i in range(len(res_batch)):
        context_list.append(
            res_batch.frames[f"{story_feat_table.lower()}.data"][i])
    context = "\n".join(context_list)

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print("LLM")

    # LLM
    query = f"""If the context is not relevant, please answer the question by using your own knowledge about the topic.
    
    {context}
    
    Question : {question}"""

    full_response = llm.generate(query)

    print(full_response)

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print(f"Total Time: {(timestamps[t_i] - timestamps[0]) * 1000:.3f} ms")


def main():
    receive_user_input()


if __name__ == "__main__":
    main()
