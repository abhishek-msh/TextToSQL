from src.bi_assistant import biAssistant
from src.types import GetAnswerModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from src.custom_exception import CustomException
from src.types import GetAnswerModel
from src.utils import api_response_builder

app = FastAPI(
    title="BI Assistant API",
    description="API for BI Assistant",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "BI Assistant API is running"}


@app.post("/get_answer", response_model=dict, tags=["BI Assistant"])
async def get_answer(data: GetAnswerModel):
    """
    Endpoint to get the answer from the BI Assistant.
    """
    bi_assistant_obj = biAssistant(data=data)
    try:
        conversation_analytics, retrieval_logs = bi_assistant_obj.get_answer()
        # Save analytics and logs to the database
        conversation_analytics.to_sql()
        retrieval_logs.to_sql(conversation_analytics=conversation_analytics)
    except CustomException as custom_exc:
        bi_assistant_obj.conversation_analytics.error = custom_exc.error
        custom_exc.conversation_analytics = bi_assistant_obj.conversation_analytics
        bi_assistant_obj.conversation_analytics.to_sql()
        bi_assistant_obj.retrieval_logs.to_sql(
            conversation_analytics=bi_assistant_obj.conversation_analytics
        )
        raise custom_exc
    return api_response_builder(conversation_analytics=conversation_analytics)


@app.post("/get_answer_streaming", response_model=dict, tags=["BI Assistant"])
async def get_answer_streaming(data: GetAnswerModel):
    """
    Endpoint to get the answer from the BI Assistant with streaming.
    """
    bi_assistant_obj = biAssistant(data=data)
    try:

        def stream():
            yield f"data: [START]\n\n"
            for item in bi_assistant_obj.get_answer_streaming():
                if not item or not str(item).strip():
                    continue
                yield f"""event: "delta"\ndata: {item}\n\n"""
            yield f"data: [DONE]\n\n"

    except CustomException as custom_exc:
        bi_assistant_obj.conversation_analytics.error = custom_exc.error
        custom_exc.conversation_analytics = bi_assistant_obj.conversation_analytics
        bi_assistant_obj.conversation_analytics.to_sql()
        bi_assistant_obj.retrieval_logs.to_sql(
            conversation_analytics=bi_assistant_obj.conversation_analytics
        )
        raise custom_exc
    return StreamingResponse(stream(), media_type="text/event-stream")
