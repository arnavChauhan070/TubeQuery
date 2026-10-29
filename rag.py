from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings,ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from urllib.parse import urlparse, parse_qs
from config import (GOOGLE_API_KEY,EMBEDDING_MODEL,CHAT_MODEL,CHUNK_SIZE,CHUNK_OVERLAP,RETRIEVAL_K,RETRIEVER_SEARCH_TYPE)
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core import documents
import re,time,os

#Ingestion



#Variables
embedding_model_name = EMBEDDING_MODEL
api_key = GOOGLE_API_KEY
youtube_url = "https://youtu.be/4Vz6L8B73i4?si=GGOJm9uOvEhzS2Cr"
chat_model = CHAT_MODEL


def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from a supported YouTube URL."""

    parsed_url = urlparse(url.strip())
    hostname = (parsed_url.hostname or "").lower()

    # Standard YouTube URLs
    if hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed_url.path == "/watch":
            video_id = parse_qs(parsed_url.query).get("v", [None])[0]

        elif parsed_url.path.startswith(("/embed/", "/shorts/", "/live/")):
            video_id = parsed_url.path.split("/")[2]

        else:
            video_id = None

    # Shortened youtu.be URLs
    elif hostname == "youtu.be":
        video_id = parsed_url.path.strip("/").split("/")[0]

    else:
        raise ValueError("Please provide a valid YouTube URL.")

    # YouTube video IDs are 11 characters
    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Could not extract a valid YouTube video ID.")

    return video_id

def fetch_transcript(video_id,lang):
    try:
        yt = YouTubeTranscriptApi()
        fetch_transcript = yt.fetch(video_id=video_id,languages=lang)
        raw_transcript = fetch_transcript.to_raw_data()


        transcript = " ".join(chunk["text"] for chunk in raw_transcript)
        return transcript
    except Exception as e:
        print(f"Exception Caught \n{e}")



splitter = RecursiveCharacterTextSplitter(
    chunk_size = CHUNK_SIZE,
    chunk_overlap = CHUNK_OVERLAP
)

def ingestion(video_id : str,lang : list[str] = ["en"]):
    """
    1. Extract YOUTUBE ID
    2. Gets its TRANSCRIPTION by youtube api
    3. Create Chunks of it 
    4. Create its Embedding
    5. Store into Vector_Store
    """
    video_id = extract_video_id(video_id)

    embedding_model = GoogleGenerativeAIEmbeddings(
    model = embedding_model_name,
    api_key = api_key
    )

    # this just creates a string with name faiss_idx/video_id

    index_dir = os.path.join("faiss_idx",video_id)

    if os.path.exists(index_dir):
        print("Loading Faiss")
        return FAISS.load_local(
            index_name=index_dir,
            embeddings=embedding_model,
            allow_dangerous_deserialization=True
        )
    

    transcript_text = fetch_transcript(video_id=video_id,lang=lang)
    
    if transcript_text is None:
        raise ValueError("Transcript Text is Empty?")
    
    chunks = splitter.create_documents(
    [transcript_text]
    )

    print("number of chunks : ",len(chunks))

   
    
    vector_store = vector_embeddings(chunks=chunks,embedding_model=embedding_model)
    vector_store.save_local(index_dir)
    return vector_store

"""
To combine like when u use retirever and it gives top k results
Those are docuemnts so to just make that those k into one paragraph we
just use this helper function
"""
def vector_embeddings(chunks,embedding_model):

    """
    Here, Since google emedding hit rate limit
    Altough 100 chunks goes in 1 call but those 100 chunks create seprate call
    creating 100 rpm and google limit is 100 rpm so 1 batch exceeds limit
    better we send them in batches 

    """

    chunk_len = len(chunks)
    batch_size = 40
    vector_store = None
    
    for i in range(0, chunk_len,batch_size):

        batch = chunks[i : i + batch_size]
        print(f"Start of batch {i} and end of batch {i + batch_size}")
        try:
            if vector_store == None:
                vector_store = FAISS.from_documents(
                    documents=batch,
                    embedding=embedding_model
                )
            else:
                vector_store.add_documents(batch)
            
            time.sleep(30)
        except Exception as e:
            print(f"Exception Caught : {e}")
            break
        

    return vector_store



    # vector_Store = FAISS.from_documents(
    # documents=chunks,
    # embedding=emedding_model
    # )
def retriever_formatting(retireived_docs : documents):
    return "/n/n".join(docs.page_content for docs in retireived_docs)

#ingestion call
vector_store = ingestion(youtube_url)

# Step 2 Retirevier 

retriever = vector_store.as_retriever(
    search_type = RETRIEVER_SEARCH_TYPE,
    search_kwargs = {"k" : RETRIEVAL_K }
)


#step 3 augmentation


llm = ChatGoogleGenerativeAI(
    model = chat_model,
    temperature = 0.2,
    google_api_key = api_key
)

prompt = PromptTemplate(
    template="""
     You are helpful assistant.
     Your task is to give answer to the question from the given context only.
     If the context is not sufficent , just return "I DON'T KNOW :( "

     {context}
     Question : {question}
""",
    input_variables = ['context','question']
)


#Chain building

"""
Everything inside `RunnableParallel` must be a Runnable or something 
LangChain can coerce into a Runnable.
Built-in LangChain components, such as retrievers and prompts, 
already implement the Runnable interface.
Custom Python functions are not automatically Runnables, 
so we can wrap them using `RunnableLambda` to make them compatible 
with LangChain's Runnable pipeline.
"""
parallel_chain = RunnableParallel(
    {
       "context" : retriever | RunnableLambda(retriever_formatting),
       "question" : RunnablePassthrough()
    }
)
str_parser = StrOutputParser()
main_chain = parallel_chain | prompt | llm | str_parser
ques = "According to Dr. Sahar Yousef, how long should an ideal focused work block be before taking a break, and how long should the break last?"
res = main_chain.invoke(ques)

print(res)