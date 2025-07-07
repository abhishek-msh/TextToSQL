from config import DatabaseConfig
from typing import List, Dict
from datetime import datetime, timezone


def _texttosql_prompt(
    user_input: str,
    tenant_id: str,
    metadata_info: str,
    relationship_diagram: str,
    example_sql=None,
) -> List[Dict[str, str]]:
    tenant_info = f"tenantid='{tenant_id}'"
    return_key_dialect = list(DatabaseConfig().DIALECT.keys())[0]
    prompt_dialect = DatabaseConfig().DIALECT[return_key_dialect]
    current_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
    current_timestamp = datetime.now(timezone.utc).timestamp()

    prompt = """You are a {dialect} expert. You need to generate a {dialect} SQL query to answer the question. our response should ONLY be based on the given context and follow the response guidelines and format instructions.

===CRITICAL DATABASE ACCURACY REQUIREMENTS*:
   - YOU MUST USE **EXACT TABLE AND COLUMN NAMES** AS PROVIDED IN THE SCHEMA - no variations, abbreviations or interpretations allowed
   - ALWAYS include TENANT INFORMATION in the query to ensure it is scoped correctly
   - Use `IN` operator for filtering, not `=` operator, when checking against multiple values
   - Use `LOWER(column_name) ILIKE LOWER('%pattern%')` for case-insensitive matches

===INPUT CONTEXT:
- Tenant Information: {tenant_info}
- Current Date and Time: Use this for queries which require current date and time
    Date and Time: {current_datetime}
    Timestamp: {current_timestamp}

===Database Schema:
# DATABASE INFORMATION:
{database_info}

# TABLES AND COLUMNS: These tables and columns are available for constructing the query:
{metadata_info}

# TABLE RELATIONSHIPS:
{relationship_diagram}

==={dialect} Syntax Guidelines:
{custom_guidelines}

===THOUGHT PROCESS: Follow these steps to construct the query: (Use CTE-Filtered Dimension Join Approach)
1. Analyze the question to identify the key entities and relationships involved.
2. Map the entities to the corresponding tables and columns in the provided schema.
3. Construct the **{dialect} Syntax** query step-by-step, ensuring all references are accurate and scoped to the tenant.
4. **CTE-Filtered Dimension Join Approach** - Construct the query using CTEs (Common Table Expressions) to filter dimensions before joining, which optimizes performance and reduces unnecessary data processing. You start by defining a Common Table Expression (CTE) that selects only the intermediate rows you actually need. Because you apply the wildcard ILIKE filters inside this CTE, you trim the dimension down to just the required records before any joins occur, keeping the rest of your query lean and fast.
5. Validate the final query against the schema to ensure it meets all accuracy requirements.
6. Format the query according to the specified **RESPONSE GUIDELINES** below, ensuring clarity and correctness.

===RESPONSE GUIDELINES:
1. Case-insensitive match – always. `LOWER(col) ILIKE LOWER('%text%')`
2. Partial names – use a ILIKE chain, not IN: When you need to match fragments of names (e.g., “ABC”, “PQR”, “XYZ”) use case-insensitive ILIKE expressions instead of IN, which only matches exact strings. (LOWER(col) ILIKE '%abc%' OR LOWER(col) ILIKE '%pqr%' OR LOWER(col) ILIKE '%xyz%')
3. Query Construction
- BUILD query in components: (WITH cte AS ( … ) SELECT … FROM   main m JOIN   other o ON … WHERE  filters GROUP  BY … HAVING … ORDER  BY … LIMIT  n;)
    1. **CTE(s)** – declare reusable, pre-filtered sets with `WITH … AS ( … )`.
    2. **SELECT** – list required columns or aggregates, plus clear aliases.
    3. **FROM** – choose the driving table and give it a short alias.
    4. **JOIN** – attach related tables/CTEs using explicit `ON` conditions.
    5. **WHERE** – apply business filters (tenant, status, soft-delete, dates, etc.).
    6. **GROUP BY / HAVING** – add aggregation and post-aggregation filters when needed.
    7. **ORDER BY** – sort the final output if presentation order matters.
    8. **LIMIT / OFFSET** – cap rows for sampling, pagination, or performance tuning.
4. If the provided context is insufficient, please explain why it can't be generated. Return in the format: `{return_key_dialect}_query: "Insufficient context to generate the query."`
5. If the question has been asked and answered before, please repeat the answer exactly as it was given before.
6. Ensure that the output **{dialect} Syntax** Query is {dialect}-compliant and executable, and free of syntax errors.

===OUTPUT FORMAT:
- A JSON dictionary with the following key-value pair:
   - {return_key_dialect}_query: Correct {dialect} SQL query string with all required columns and conditions following Query Construction (CTE-Filtered Dimension Join Approach).
   
===EXAMPLES:
{example_string}

===Notes: 
1. Never compare any `UUID` datatype column with a name or `STRING` or `ARRAY` value.
2. Maintain the Output Format strictly as a JSON object with the key `{return_key_dialect}_query`.
3. You are restricted to use only the provided column names and table names as they are, without any modifications or assumptions.
4. HINT: IF No operator matches the given name and argument types. You might need to add explicit type casts."""

    example_string = ""
    if example_sql:
        for example in example_sql:
            example_string += f"User Question: {example['question']}\n"
            example_string += f"{return_key_dialect}_query: {example['sqlQuery']}\n\n"

    messages = [
        {
            "role": "system",
            "content": prompt.format(
                dialect=prompt_dialect,
                current_datetime=current_datetime,
                current_timestamp=current_timestamp,
                tenant_info=tenant_info,
                database_info=DatabaseConfig().DATABASE_INFORMATION_PROMPT_TEMPLATE,
                metadata_info=metadata_info,
                relationship_diagram=relationship_diagram,
                custom_guidelines=DatabaseConfig().TEXT_TO_SQL_PROMPT_TEMPLATE,
                return_key_dialect=return_key_dialect,
                example_string=example_string,
            ),
        },
    ]
    print(
        prompt.format(
            dialect=prompt_dialect,
            current_datetime=current_datetime,
            current_timestamp=current_timestamp,
            tenant_info=tenant_info,
            database_info=DatabaseConfig().DATABASE_INFORMATION_PROMPT_TEMPLATE,
            metadata_info=metadata_info,
            relationship_diagram=relationship_diagram,
            custom_guidelines=DatabaseConfig().TEXT_TO_SQL_PROMPT_TEMPLATE,
            return_key_dialect=return_key_dialect,
            example_string=example_string,
        )
    )

    # if example_sql:
    #     for example in example_sql:
    #         messages.append(
    #             {
    #                 "role": "user",
    #                 "content": example["question"],
    #             }
    #         )
    #         messages.append(
    #             {
    #                 "role": "assistant",
    #                 "content": "{"
    #                 + return_key_dialect
    #                 + "_query: "
    #                 + example["sqlQuery"]
    #                 + "}",
    #             }
    #         )
    messages.append(
        {
            "role": "user",
            "content": f"User Query: {user_input}",
        }
    )
    # print(messages)
    return messages


def _query_rephrase_prompt(
    query: str,
    previous_conversation: str,
) -> List[Dict[str, str]]:
    prompt = """You are a query rephrasing tool that rephrases follow-up questions into standalone questions (without any modification in entity values) which can be understood independently without relying on previous question and answer.

Objective: Analyze the chat history enclosed within triple backticks, carefully to create standalone question independent of terms like 'it', 'that', etc.
For queries that are not a follow-up ones or not related to the conversation, you will respond with a predetermined message: 'Not a follow-up question'

**Critical Instructions:**

1. **Entity Integrity Rule:**

   * You must **never modify, correct, or infer any entity value** from the user question.
   * **Do not change, adjust, or spell-correct any names, emails, IDs, dates, numbers, or phrases, including typos, formatting, or capitalization.**
   * Copy all such values and phrases **exactly as written by the user**, even if they appear misspelled or oddly formatted.

2. If the original user query already contains a misspelled or uniquely written entity, do **not** alter it.

   * For example, 'ajinkya.bhale' must stay as 'ajinkya.bhale', and 'Raj Patel' as 'Raj Patel'.

## CHAT HISTORY:
```
{previous_conversation}
```

## Output Format:
    A JSON dict with 1 key:
        - 'rephrased_query'(str): It Contains the rephrased query formed by following the above instructions."""
    prompt = prompt.format(previous_conversation=previous_conversation)
    messages = []
    messages.append({"role": "system", "content": prompt})
    messages.append({"role": "user", "content": f"""Query: {query}"""})
    return messages


def _answer_prompt(
    user_input: str,
    sql_query: str,
    sql_result: str,
) -> List[Dict[str, str]]:
    prompt = """You are an assistant that translates SQL query results into clear, natural language responses for end users.

Given the following inputs:

- **Question**: {query}  
- **SQL Query**: {sql_query}  
- **SQL Result**: {result}  

### Output Format (strict):
Return a single **JSON object** with this exact structure:
- "answer": <Your well-structured Markdown-formatted natural language answer here>"""
    messages = [
        {
            "role": "system",
            "content": prompt.format(
                query=user_input, sql_query=sql_query, result=sql_result
            ),
        },
    ]
    return messages


def _graph_prompt(
    user_input: str, sql_query: str, data_type: str
) -> List[Dict[str, str]]:
    visualize_system_msg = """The following is a pandas DataFrame that contains the results of the query that answers the question the user asked: '{query}'

The DataFrame was produced using this query: {sql}

The following is information about the resulting pandas DataFrame 'df':
Running df.dtypes gives:
{data_types}"""

    visualize_user_msg = """Can you generate the Python plotly code to insightfully chart the results of the dataframe? Assume the data is in a pandas dataframe called 'df'. If there is only one value in the dataframe, use an Indicator. Respond with only Python code. Do not answer with any explanations -- just the code."""
    messages = [
        {
            "role": "system",
            "content": visualize_system_msg.format(
                query=user_input, sql=sql_query, data_types=data_type
            ),
        },
        {
            "role": "user",
            "content": visualize_user_msg,
        },
    ]
    return messages


def _cluster_identification_prompt(
    user_input: str,
) -> List[Dict[str, str]]:
    prompt = """You are a senior data-modelling specialist with expertise in database schema design and data cleaning.
Your task is to analyze user query and accurately determine which clusters/categories of data are relevant to the query.
If a query spans multiple domains, assign all applicable clusters/categories.

## Clusters:
1. `work_item_management`: Everything required to create, identify, tag, assign, track status, and repeat (recurrence) individual work items / tasks, plus the lookup tables that relate work-item types to projects.
2. `project_workspace_management`: Structures that group work into higher-level containers (projects and workspaces), connect them to users, features, views, and schedules, and store per-project configuration.
3. `user_management`: Core user profile data plus auxiliary tables for clones, devices, saved entity views, and websocket connection hosts.
4. `time_logging`: Captures time entries, contains time-tracking metadata, and links to work items or projects.
5. `roles_permissions`: Defines role hierarchies and the mappings that grant those roles to users.
6. `features_packages`: Catalogues individual features, groups them, bundles them into packages, and stores package-level pricing configuration.
7. `subscription_billing`: Tracks tenant subscriptions, their status, usage, and historical or sub-level consumption data for billing.
8. `tags_categorization`: Vocabulary for tagging work items or other entities for flexible search and categorisation.
9. `workflow_management`: Generic workflow engine metadata and the mapping of workflow steps to status states.
10. `tenant_registration`: Multi-tenant onboarding and master tenant records, plus user registration details tied to tenants or workflows.
11. `custom_fields`: Tenant-level custom field catalogue and the display-order rules for those fields across entities.

### Classification Task:
Given the user query, output the relevant clusters/categories from the list above.

### Output Format:
A JSON dictionary with the following key-value pair:
- "clusters": [<list of relevant clusters/categories>]"""
    messages = [
        {
            "role": "system",
            "content": prompt,
        },
        {
            "role": "user",
            "content": f"User Query: {user_input}",
        },
    ]
    return messages
