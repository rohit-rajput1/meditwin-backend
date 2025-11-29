from database.models.report_type import ReportType
from .prompts import SYSTEM_PROMPT,AGGREGATED_PROMPTS

def build_prompt(report_type_name: str, report_data: dict, chat_history):
    """
    Builds the full OpenAI prompt using system prompt, report insights
    and chat history.
    """

    # Select report-specific aggregated prompt if available
    if report_type_name in AGGREGATED_PROMPTS:
        context_prompt = AGGREGATED_PROMPTS[report_type_name].format(
            report_data=report_data
        )
    else:
        context_prompt = "The user's medical report details are below.\n" + str(report_data)

    # final system message
    system_message = f"""
        {SYSTEM_PROMPT}

        ==== REPORT DATA ====
        {context_prompt}
        ==== END REPORT DATA ====
    """

    messages = [{"role": "system", "content": system_message}]

    # Add the entire chat history
    for msg in chat_history:
        messages.append({"role": "user", "content": msg.user_query})
        messages.append({"role": "assistant", "content": msg.bot_response})

    return messages



