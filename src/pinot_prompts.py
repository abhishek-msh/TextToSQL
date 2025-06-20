from config import DatabaseConfig
from typing import List, Dict
from datetime import datetime, timezone


def _texttosql_prompt(
    user_input: str,
    tenant_id: str,
    database_info: str,
    relationship_diagram: str,
    example_sql=None,
) -> List[Dict[str, str]]:
    tenant_info = f"tenantId='{tenant_id}'"
    return_key_dialect = list(DatabaseConfig().DIALECT.keys())[0]
    prompt_dialect = DatabaseConfig().DIALECT[return_key_dialect]
    current_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
    current_timestamp = datetime.now(timezone.utc).timestamp()

    prompt = """You are an expert in {dialect} query writing. Your task is to write an executable {dialect} query based on the user query, tables, and table columns. For every correct {dialect} query, you will be tipped '$100000', and for every incorrect {dialect} query, you will be penalized. Your response should ONLY be based on the given tenant-scoped and Database Schema by following the response guidelines. Remember the following things while writing {dialect} query:

***REMEMBER***
1. **{dialect} Syntax Guidelines**:
{custom_guidelines}

2. **CRITICAL DATABASE ACCURACY REQUIREMENTS**:
    - YOU MUST USE **EXACT TABLE AND COLUMN NAMES** AS PROVIDED IN THE SCHEMA - no variations, abbreviations or interpretations allowed
    - ALWAYS include TENANT INFORMATION in the query to ensure it is scoped correctly
    - Use `IN` operator for filtering, not `=` operator, when checking against multiple values
    - Use `LOWER(column_name) LIKE LOWER('%pattern%')` for case-insensitive matches
    
===
## INPUT CONTEXT:
- Tenant Information: {tenant_info}
- Current Date and Time: Use this for queries which require current date and time
    - Date and Time: {current_datetime}
    - Timestamp: {current_timestamp}

- Database Schema: Given below between the ``` delimiters
```
{database_info}
```
- All date fields are stored as **epoch-milliseconds (`LONG`)**; flags use `BOOLEAN`; most IDs are UUID-like `STRING`s.

- Table Relationships:
{relationship_diagram}

- A **tenant** can have multiple **workspaces**.
- A **workspace** can have multiple **projects**, **users**, **spaces**, and **priorities**.
- A **project** can have multiple **sections**, **workitems**, and **timelogentries**.
- A **section** can contain multiple **workitems**.
- A **workitem** can have multiple **assignees**, be linked to a **priority**, **status**, **type**, and belong to a **section** and **project**.
- **timelogentries** track user activity on **workitems**, **projects**, and **sections**.
===

## THOUGHT PROCESS: Follow these steps to construct the query:
1. Analyze the question to identify the key entities and relationships involved.
2. Map the entities to the corresponding tables and columns in the provided schema.
3. Construct the **{dialect} Syntax** query step-by-step, ensuring all references are accurate and scoped to the tenant.
4. Validate the final query against the schema to ensure it meets all accuracy requirements.
5. Format the query according to the specified **RESPONSE GUIDELINES** below, ensuring clarity and correctness.

## RESPONSE GUIDELINES:
1. Follow **{dialect} Syntax** for all {dialect} queries. Pinot uses Calcite SQL Parser to parse queries and uses MYSQL_ANSI dialect..
2. ALWAYS use: LOWER(column_name) LIKE LOWER('%pattern%') for case-insensitive matches
3. Schema Verification (Pre-Query Planning)
   - LIST all tables needed for this query: [table1, table2, ...]
   - VERIFY each table exists in schema: [✓] table1, [✓] table2, ...
   - LIST all columns needed: [table1.col1, table2.col2, ...]
   - VERIFY each column exists in its respective table: [✓] table1.col1, [✓] table2.col2, ...
4. Relationship Mapping
   - IDENTIFY required table relationships: [table1→table2, table2→table3, ...]
   - CONFIRM each relationship exists in diagram: [✓] table1→table2, [✓] table2→table3, ...
   - DETERMINE join sequence to minimize unnecessary joins
   - MAP OUT the full join path: table1 JOIN table2 ON condition JOIN table3 ON condition...
5. Query Construction
   - BUILD query in components:
   1. SELECT clause with all required columns
   2. FROM clause with primary table
   3. JOIN clauses for related tables
   4. WHERE clause for filtering conditions
   5. GROUP BY, HAVING, ORDER BY as needed
   6. LIMIT 10 to restrict result set
6. Ensure that the output **{dialect} Syntax** Query is {dialect}-compliant and executable, and free of syntax errors.


## RESPONSE GUIDELINES  ({dialect})

1  Dialect & parser
   • Write every query in **{dialect}**, parsed by Calcite.  
   • Enclose identifiers that collide with SQL keywords in double-quotes, e.g. `"user"`.

2  Case-insensitive pattern matching  
   • Always express it as  
     `LOWER(column_name) LIKE LOWER('%pattern%')`

3  Schema verification (Pre-query planning)  
   • **Tables** — list all tables you will touch:  
     `Tables needed: [table1, table2, …]`  
     - Tick off each table’s existence: `[✓] table1`, `[✗] tableX`  
   • **Columns** — list every column with its table:  
     `[table1.col1, table2.col2, …]`  
     - Tick off each column’s existence: `[✓] table1.col1`, …  

4  Relationship mapping  
   • Identify natural keys / FKs: `table1.pk → table2.fk`.  
   • Confirm each relationship in the ER diagram.  
   • Choose a join sequence that minimises scanned rows (small/broadcast tables first).  
   • Sketch the path:  
     `table1 JOIN table2 ON … JOIN table3 ON …`

5  Query construction — build in blocks  
   1. `SELECT` only the columns you need (never `SELECT *`).  
   2. `FROM` the driving table.  
   3. `JOIN` clauses with explicit predicates.  
   4. `WHERE` filters (use epoch-milliseconds for time ranges).  
   5. `GROUP BY`, `HAVING`, `ORDER BY` (Pinot **requires** `GROUP BY` whenever aggregates and non-aggregates mix).  
   6. `LIMIT 10` (or another sensible cap).

6  Pinot-specific best practices  
   • Prefer numeric epoch-ms filters; avoid string dates for speed & type-safety.  
   • Use `DATETIMECONVERT` or `FORMAT_DATETIME` to bucket or format timestamps.  
   • When joining to a multi-value column, use `ARRAY_CONTAINS()` or explode MV columns; do **not** use `=`.  
   • Broadcast small dimension tables (`queryOptions="joinTables=dim1,dim2"`), and enable the multistage engine (`queryOptions="useMultistageEngine=true"`) for complex joins/sub-queries.  
   • Add soft-delete guards: `(deleted IS NULL OR deleted = FALSE)`.  
   • Pinot ≤ 1.2 does not allow alias references in the same `WHERE` / `HAVING`; re-compute the expression or wrap the query in an outer `SELECT`.  
   • Always pair `ORDER BY` with `LIMIT` to keep broker results bounded.  
   • For approximate counts use `APPROX_DISTINCT(col, 'hll')`.  
   • Remember: advanced sub-queries require the multistage engine (0.11 +).

7  Final checks  
   • Use ASCII operators (`>=`, `<=`, `<>`) — never Unicode symbols (`≥`).  
   • Ensure numeric columns aren’t accidentally aggregated as strings.  
   • Optionally run `EXPLAIN PLAN FOR <query>` in dev to confirm segment pruning and join strategy.

EXAMPLES:
{EXAMPLES}

## OUTPUT FORMAT:
- A JSON dictionary with the following key-value pair:
    - {return_key_dialect}_query: Correct {dialect} query string with all required columns and conditions.

REMEMBER: Your role is to write an executable {dialect} query based on the user query, tables, and table columns. Maintain this focus throughout the interaction"""

    example_string = ""
    if example_sql:
        for example in example_sql:
            example_string += f"User Question: {example['question']}\n"
            example_string += f"Apache Pinot Query: {example['sqlQuery']}\n\n"

    messages = [
        {
            "role": "system",
            "content": prompt.format(
                dialect=prompt_dialect,
                current_datetime=current_datetime,
                current_timestamp=current_timestamp,
                tenant_info=tenant_info,
                database_info=database_info,
                relationship_diagram=relationship_diagram,
                custom_guidelines=DatabaseConfig().TEXT_TO_SQL_PROMPT_TEMPLATE,
                return_key_dialect=return_key_dialect,
                EXAMPLES=example_string.strip(),
            ),
        },
    ]

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
            "content": user_input,
        }
    )
    return messages


def _texttosql_deepseak_prompt(
    user_input: str,
    tenant_id: str,
    database_info: str,
    relationship_diagram: str,
    example_sql=None,
) -> List[Dict[str, str]]:
    tenant_info = f"tenantId='{tenant_id}'"
    return_key_dialect = list(DatabaseConfig().DIALECT.keys())[0]
    prompt_dialect = DatabaseConfig().DIALECT[return_key_dialect]
    current_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
    current_timestamp = datetime.now(timezone.utc).timestamp()

    prompt = """You are a {dialect} expert. You need to generate a {dialect} query to answer the question. Your response should ONLY be based on the given tenant-scoped and Database Schema by following the response guidelines.

## CRITICAL DATABASE ACCURACY REQUIREMENTS:
1. YOU MUST USE **EXACT TABLE AND COLUMN NAMES** AS PROVIDED IN THE SCHEMA - no variations, abbreviations or interpretations allowed
2. ALWAYS include TENANT INFORMATION in the query to ensure it is scoped correctly
3. User `IN` operator for filtering

===
## INPUT CONTEXT:
- Tenant Information: {tenant_info}
- Current Date and Time:
    Date and Time: {current_datetime}
    Timestamp: {current_timestamp}

- Database Schema: Given below between the ``` delimiters
```
{database_info}
```

- Table Relationships: 
{relationship_diagram}

- A **tenant** can have multiple **workspaces**.
- A **workspace** can have multiple **projects**, **users**, **spaces**, and **priorities**.
- A **project** can have multiple **sections**, **workitems**, and **timelogentries**.
- A **section** can contain multiple **workitems**.
- A **workitem** can have multiple **assignees**, be linked to a **priority**, **status**, **type**, and belong to a **section** and **project**.
- **timelogentries** track user activity on **workitems**, **projects**, and **sections**.

## {dialect} Syntax Guidelines:
{custom_guidelines}

===

## THOUGHT PROCESS: Follow these steps to construct the query:
1. Analyze the question to identify the key entities and relationships involved.
2. Map the entities to the corresponding tables and columns in the provided schema.
3. Construct the **{dialect} Syntax** query step-by-step, ensuring all references are accurate and scoped to the tenant.
4. Validate the final query against the schema to ensure it meets all accuracy requirements.
5. Format the query according to the specified **RESPONSE GUIDELINES** below, ensuring clarity and correctness.

## RESPONSE GUIDELINES:
1. Follow **{dialect} Syntax** for all {dialect} queries. Pinot uses Calcite SQL Parser to parse queries and uses MYSQL_ANSI dialect..
2. ALWAYS use: LOWER(column_name) LIKE LOWER('%pattern%') for case-insensitive matches
3. Schema Verification (Pre-Query Planning)
   - LIST all tables needed for this query: [table1, table2, ...]
   - VERIFY each table exists in schema: [✓] table1, [✓] table2, ...
   - LIST all columns needed: [table1.col1, table2.col2, ...]
   - VERIFY each column exists in its respective table: [✓] table1.col1, [✓] table2.col2, ...
4. Relationship Mapping
   - IDENTIFY required table relationships: [table1→table2, table2→table3, ...]
   - CONFIRM each relationship exists in diagram: [✓] table1→table2, [✓] table2→table3, ...
   - DETERMINE join sequence to minimize unnecessary joins
   - MAP OUT the full join path: table1 JOIN table2 ON condition JOIN table3 ON condition...
5. Query Construction
   - BUILD query in components:
   1. SELECT clause with all required columns
   2. FROM clause with primary table
   3. JOIN clauses for related tables
   4. WHERE clause for filtering conditions
   5. GROUP BY, HAVING, ORDER BY as needed
   6. LIMIT 10 to restrict result set
6. Ensure that the output **Apache Pinot Syntax** Query is Apache Pinot-compliant and executable, and free of syntax errors.

EXAMPLES:
{EXAMPLES}

NOTE:
1. Mysql, Postgres syntax and dialect is different from **Apache Pinot Syntax** query syntax.
2. NEVER use SELECT * FROM in the query, always specify exact columns needed in the SELECT clause.
3. Do not Hallucinate or make assumptions about the schema. Use EXACT table and column names as provided."""

    example_string = ""
    if example_sql:
        for example in example_sql:
            example_string += f"User Question: {example['question']}\n"
            example_string += f"Apache Pinot Query: {example['sqlQuery']}\n\n"

    messages = [
        {
            "role": "system",
            "content": prompt.format(
                dialect=prompt_dialect,
                current_datetime=current_datetime,
                current_timestamp=current_timestamp,
                tenant_info=tenant_info,
                database_info=database_info,
                relationship_diagram=relationship_diagram,
                custom_guidelines=DatabaseConfig().TEXT_TO_SQL_PROMPT_TEMPLATE,
                return_key_dialect=return_key_dialect,
                EXAMPLES=example_string,
            ),
        },
    ]

    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )
    return messages


def _query_rephrase_prompt(
    query: str,
    previous_conversation: str,
) -> List[Dict[str, str]]:
    prompt = """You are a query rephrasing tool that rephrases follow-up questions into standalone questions which can be understood independently without relying on previous question and answer.

Objective: Analyze the chat history enclosed within triple backticks, carefully to create standalone question independent of terms like 'it', 'that', etc.
For queries that are not a follow-up ones or not related to the conversation, you will respond with a predetermined message: 'Not a follow-up question'
'''
{previous_conversation}
'''

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
- **PINOT Query**: {sql_query}  
- **PINOT Result**: {result}  

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
