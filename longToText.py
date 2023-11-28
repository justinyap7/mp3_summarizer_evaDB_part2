import os
import time
import evadb
import os
import time
from time import perf_counter
import tkinter as tk
import sys
from gpt4all import GPT4All
from unidecode import unidecode
from tkinter import filedialog
from tkinter import messagebox
from google.cloud import storage
from google.cloud import speech
from google.cloud.exceptions import NotFound, Forbidden

# # Set the path to your service account key
# service_account_key = ''
# os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_key

# # Initialize a storage client
# storage_client = storage.Client()

APP_SOURCE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_VIDEO_PATH = os.path.join(
    APP_SOURCE_DIR, "benchmarks", "testPodcast.mp3")
# temporary file paths
TRANSCRIPT_PATH = os.path.join("evadb_data", "tmp", "transcript.txt")
OUTPUT_PATH = os.path.join("evadb_data", "tmp", "output.txt")



# Function to create a bucket
def create_bucket(bucket_name, location='US'):
    """Create a new bucket in specific location."""
    bucket = storage_client.bucket(bucket_name)
    bucket.storage_class = "STANDARD"
    new_bucket = storage_client.create_bucket(bucket, location=location)
    print(f"Bucket {new_bucket.name} created.")
    return new_bucket

def blob_exists(bucket_name, blob_name):
    """Check if a blob exists in the given GCS bucket"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    return blob.exists()

def bucket_exists(bucket_name):
    """Check if a GCS bucket exists."""
    storage_client = storage.Client()
    try:
        storage_client.get_bucket(bucket_name)
        return True
    except NotFound:
        # The bucket does not exist or you have no access.
        return False
    except Forbidden:
        # You do not have permission to access the bucket.
        return False


# Function to upload a file to the bucket
def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")
    return f"gs://{bucket_name}/{destination_blob_name}"

def transcribe_gcs(gcs_uri):
    """Transcribes an audio file located in Google Cloud Storage."""
    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        # You might need to change the encoding and sample rate hertz
        # based on your specific MP3 file
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
        sample_rate_hertz=48000,
        language_code="en-US",
        enable_automatic_punctuation=True
    )

    start_time = time.time()  # Start timing
    operation = client.long_running_recognize(config=config, audio=audio)
    print("Waiting for operation to complete...")
    response = operation.result(timeout=400)
    end_time = time.time()  # End timing

    transcription = " ".join([result.alternatives[0].transcript for result in response.results])

    time_taken = end_time - start_time
    print(f"Transcription time: {time_taken} seconds")

    return transcription, time_taken

def write_transcription_to_file(transcription, file_path):
    """Writes the transcription to a file."""
    with open(file_path, 'w') as file:
        file.write(transcription)
        
def select_json_file():
    file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if file_path:
        json_file_path_var.set(file_path)
        global service_account_key
        service_account_key = file_path
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = service_account_key

        # Initialize storage client here
        try:
            global storage_client
            storage_client = storage.Client()
            select_json_button.pack_forget()
            initialize_main_interface()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize Google Cloud Client: {e}")

        
def initialize_main_interface():
    # Welcome message and instructions
    welcome_label.pack(pady=10)

    # Buttons to select MP3 files
    select_mp3_button.pack(pady=5)

    # Label and entry for blob name
    blob_name_label.pack(pady=5)
    blob_name_entry.pack(pady=5)

    # Button to continue
    continue_button.pack(pady=20)

def select_mp3_file():
    file_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])
    if file_path:
        mp3_file_path_var.set(file_path)

def on_continue():
    json_file_path = json_file_path_var.get()
    mp3_file_path = mp3_file_path_var.get()
    user_input_blob_name = blob_name_var.get().strip()

    # Provide a default MP3 path if not selected
    default_mp3_path = TRANSCRIPT_PATH
    mp3_file_path = mp3_file_path if mp3_file_path else default_mp3_path
    
    

    if user_input_blob_name:
        # Hide the first screen widgets
        for widget in root.winfo_children():
            widget.pack_forget()
        
        bucket_name = 'mp3-to-text-evadb'
        source_file_name = mp3_file_path
        
        if mp3_file_path:  # Ensuring an MP3 file has been selected
            source_file_name = mp3_file_path
        else:
            messagebox.showwarning("Warning", "Please select an MP3 file.")
            return

        destination_blob_name = f"{user_input_blob_name}.mp3"


        destination_blob_name = f"{user_input_blob_name}.mp3"
        gcs_uri = f'gs://{bucket_name}/{destination_blob_name}'
        
        if not bucket_exists(bucket_name):
            # Create a bucket
            bucket = create_bucket(bucket_name)
        else:
            print("Bucket Exists")

        if not blob_exists(bucket_name, destination_blob_name):
            gcs_uri = upload_blob(bucket_name, source_file_name, destination_blob_name)
            print(f"GCS URI of uploaded file: {gcs_uri}")
        else:
            print(gcs_uri)


        transcription, time_taken = transcribe_gcs(gcs_uri)
        print(transcription)
        print(f"Time taken for transcription: {time_taken} seconds")

        # Write the transcription to the file
        write_transcription_to_file(transcription, TRANSCRIPT_PATH)
        
        ask_question(TRANSCRIPT_PATH)

        
        
        # Read from a text file and display the content
        with open(OUTPUT_PATH, "r") as file:
            content = file.read()
        text_label = tk.Label(root, text=content, wraplength=500)  # Set wraplength as per your requirement
        text_label.pack()
    else:
        messagebox.showwarning("Warning", "Please input Blob name.")        
        
        
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
    
    with open(OUTPUT_PATH, 'w') as file:
        file.write(full_response)

    t_i = t_i + 1
    timestamps[t_i] = perf_counter()
    print(f"Time: {(timestamps[t_i] - timestamps[t_i - 1]) * 1000:.3f} ms")

    print(f"Total Time: {(timestamps[t_i] - timestamps[0]) * 1000:.3f} ms")

# # Replace with your desired bucket name and file names
# bucket_name = 'mp3-to-text-evadb'
# source_file_name = 'benchmarks/testPodcast.mp3'
# destination_blob_name = 'testPodcast.mp3'
# gcs_uri = f'gs://{bucket_name}/{destination_blob_name}'

# if not bucket_exists(bucket_name):
#     # Create a bucket
#     bucket = create_bucket(bucket_name)
# else:
#     print("Bucket Exists")

# if not blob_exists(bucket_name, destination_blob_name):
#     gcs_uri = upload_blob(bucket_name, source_file_name, destination_blob_name)
#     print(f"GCS URI of uploaded file: {gcs_uri}")
# else:
#     print(gcs_uri)


# transcription, time_taken = transcribe_gcs(gcs_uri)
# print(transcription)
# print(f"Time taken for transcription: {time_taken} seconds")

# # Write the transcription to the file
# write_transcription_to_file(transcription, TRANSCRIPT_PATH)

# # Create the main window
# root = tk.Tk()
# root.title("MP3 Summarizer - EvaDB")

# # Welcome message and instructions
# welcome_label = tk.Label(root, text="Welcome to MP3 Summarizer - EvaDB!\n🔮 Welcome to EvaDB! This app lets you ask summarize any local MP3 file.\n You will only need to supply file path to the app.\nPlease select your GCS JSON key. Selecting an MP3 file is optional.")
# welcome_label.pack(pady=10)

# # Variables to hold file paths
# json_file_path_var = tk.StringVar()
# mp3_file_path_var = tk.StringVar()

# # Buttons to select JSON and MP3 files
# select_json_button = tk.Button(root, text="Select GCS JSON Key", command=select_json_file)
# select_json_button.pack(pady=5)

# select_mp3_button = tk.Button(root, text="Select MP3 File (Optional)", command=select_mp3_file)
# select_mp3_button.pack(pady=5)

# # Label and entry for blob name
# blob_name_label = tk.Label(root, text="Please name your blob to put into the bucket and if it is a new mp3, make it unique")
# blob_name_label.pack(pady=5)

# blob_name_var = tk.StringVar()
# blob_name_entry = tk.Entry(root, textvariable=blob_name_var)
# blob_name_entry.pack(pady=5)

# # Button to continue
# continue_button = tk.Button(root, text="Continue", command=on_continue)
# continue_button.pack(pady=20)

# # Run the application
# root.mainloop()
# Create the main window

root = tk.Tk()
root.title("MP3 Summarizer - EvaDB")

# Variables to hold file paths
json_file_path_var = tk.StringVar()

# Welcome message and instructions (initialized but not packed yet)
welcome_label = tk.Label(root, text="Welcome to MP3 Summarizer - EvaDB!\n🔮 Welcome to EvaDB! This app lets you summarize any local MP3 file.\n You will only need to supply file path to the app.\nPlease select your GCS JSON key. Selecting an MP3 file is optional.")

# Buttons to select MP3 files (initialized but not packed yet)
select_mp3_button = tk.Button(root, text="Select MP3 File (Optional)", command=select_mp3_file)
mp3_file_path_var = tk.StringVar()

# Label and entry for blob name (initialized but not packed yet)
blob_name_label = tk.Label(root, text="Please name your blob to put into the bucket and if it is a new mp3, make it unique")
blob_name_var = tk.StringVar()
blob_name_entry = tk.Entry(root, textvariable=blob_name_var)

# Button to continue (initialized but not packed yet)
continue_button = tk.Button(root, text="Continue", command=on_continue)

# Button to select JSON file
select_json_button = tk.Button(root, text="Select GCS JSON Key", command=select_json_file)
select_json_button.pack(pady=20)

# Run the application
root.mainloop()