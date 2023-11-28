
# MP3 Summarizer EvaDB

MP3 Summarizer EvaDB is an innovative application designed to transcribe and summarize audio content from MP3 files. Leveraging the power of SpeechRecognition, pydub, and GPT4All, it transforms spoken words into written summaries, making it easier to digest and understand audio content quickly.

[Project Repository](https://github.com/justinyap7/mp3_summarizer_evaDB)

## Features

- **Transcription**: Convert spoken language within MP3 files to text using Google Cloud API and pydub.
- **Summarization**: Summarize the transcribed text with the assistance of GPT4All's QA functionalities.
- **Ease of Use**: Simply input the path to your local MP3 file, or use the demo file provided by pressing "enter".
- **Local Processing**: Everything runs on your local machine, with no need for an external API key.

## Prerequisites

- Python >= 3.8
- Access to local MP3 files for summarization.
- Google Cloud Account and Enable Speech to Text API
- Make a new project and get a through a API key from free trial 

## Installation

Clone the repository and navigate to the project directory:

```sh
git clone https://github.com/justinyap7/mp3_summarizer_evaDB_part2.git
cd evaDB
```
## Setup
Ensure that the local Python version is >= 3.8. Install the required libraries:

```bat
pip3 install -r requirements.txt
```

### How to Run
```bash
python3 mp3ToSum.py
```

## Usage
-Run the longToText.py script.
-Select API Key .json file when prompted.
-Type in a blob name you want your mp3 to be named on your bucket
-Wait for the transcription and summarization to complete.

## Examples
-Input: MP3 filepath of "The Beggar Woman of Locarno"

-Output: Summary of the short story

## Transcription and Summarization Process
The application works in two main stages:

1. Transcription: The Google Cloud Speech to Text transcibes the MP3 and writes to transcription.txt in the tmp folder

2. Summarization: Once the transcription is complete, a temporary text file is created and its path is passed into the ask_question function from GPT4All. The function then generates a summary of the transcribed text.

## Acknowledgements
- Utilization of functionalities from ["Youtube QA"](https://github.com/Chitti-Ankith/Youtube_QA) and ["Story QA using GPT4All"](https://github.com/Chitti-Ankith/Story-QA-using-GPT4All) repositories.
