from fastapi import FastAPI,HTTPException
from app.models import userCreate,userResponse,videoCreate,videoResponse,questionCreate,questionResponse
from rag import ingestion,run_chain,get_faiss_path,load_vector_store
from app.database import user_collection,youtube_collection,question_collection,create_index
from bson import ObjectId
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app : FastAPI):
     
     print("Application Starts !!")
     await create_index()

     yield

     print("Application Closed!!")


app = FastAPI(lifespan=lifespan)


#Home

@app.get("/")
def welcome():
    return {
        "message" : "Welcome To TUBEQUERY !!"
    }


#user
@app.post("/user")
async def create_user(user : userCreate) -> userResponse:

    try:
        #first check what if user is already there
        existing_user = await user_collection.find_one(
            {
              "email" : user.email  
            }
        )

        if existing_user:
            raise HTTPException(status_code=503,detail = "Email already exists !!")
        
        res = await user_collection.insert_one(
            {
                "name" : user.name,
                "email": str(user.email)
            }
        )
    except Exception as e:
        print(f"Exception Caught : {e}")
        raise HTTPException(status_code=503,detail=f"Exception Caught /n{e}")


    return{
        "user_id" : str(res.inserted_id),
        "name" : user.name,
        "email" : str(user.email)
    }
    



@app.post("/video")
async def start_pipeline(request : videoCreate):
    youtube_url = request.video_url
    lang_list = []

    for lang in request.lang:
        print(f"Language : {lang}")
        lang_list.append(lang.value)

   
    try:
        ingestion(youtube_url,lang_list)

        res = await youtube_collection.insert_one(
            {
                "user_id" : request.user_id,
                "video_url" : request.video_url,
                "lang" :    lang_list
            }
        )
    except Exception as e:
        print(f"Exception Caught : {e}")
        raise HTTPException(status_code=502,detail=f"Something happenned!! \n {e}")

    youtube_id = res.inserted_id

    return {
        "youtube_id" : str(youtube_id)
    }

@app.post("/question")
async def post_question(request : questionCreate):
    ques = request.question

    try:
        
        # checking if the video_url exits or not!
        video_obj = await youtube_collection.find_one({
            "_id" : ObjectId(request.video_id)
        })

        if video_obj is None:
            raise HTTPException(status_code=404,detail="Video URL not present!!")
        
        question = video_obj.question

        
        youtube_url = video_obj["video_url"]


        idx_dir = get_faiss_path(youtube_url)
        vector_store = load_vector_store(idx_dir)

        answer = run_chain(ques,vector_store)
        res = await question_collection.insert_one({
            "video_id" : request.video_id,
            "question": request.question,
            "answer" : answer
        })
    except Exception as e:
        print(f"Exception Caught : {e}")
        raise HTTPException(status_code=503,detail=f"Exception /n{e}")

    question_id = res.inserted_id
  
    return{
        "question_id" : str(question_id),
        "answer" : answer,  
    }
