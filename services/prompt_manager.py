"""
Prompt management and intent detection
"""
import json
import re
from typing import List, Dict
import structlog
from utils.helpers import Utils

logger = structlog.get_logger()

class PromptManager:
    """Centralized prompt and intent management with enhanced GROUP BY rules"""
    
    def __init__(self, ai_services):
        self.ai_services = ai_services
    
    def load_base_prompt(self):
        """Enhanced base prompt with comprehensive few-shot learning"""
        
        few_shot_examples = """
------ EXAMPLE 1: Revenue Analysis with Proper Client Filtering
User: Show me revenue for Brown Ltd in 2024 and 2025
System: You need to filter by client and use DATEPART for year extraction from date columns:

SELECT 
    [Client],
    DATEPART(YEAR, [Date]) AS [Year],
    SUM([Revenue]) AS [Total_Revenue]
FROM [dbo].[Financial] 
WHERE [Client] = 'Brown Ltd' 
    AND DATEPART(YEAR, [Date]) IN (2024, 2025)
GROUP BY [Client], DATEPART(YEAR, [Date])
ORDER BY [Year];

------ EXAMPLE 2: Contextual Follow-up Analysis with Context Preservation
User: Why does the revenue behave this way?
System: To analyze revenue behavior, calculate growth rates and trends using the same client filter from previous query:

SELECT 
    [Client],
    DATEPART(YEAR, [Date]) AS [Year],
    DATEPART(QUARTER, [Date]) AS [Quarter],
    SUM([Revenue]) AS Quarterly_Revenue,
    LAG(SUM([Revenue])) OVER (
        PARTITION BY [Client] 
        ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
    ) AS Previous_Quarter,
    CASE 
        WHEN LAG(SUM([Revenue])) OVER (
            PARTITION BY [Client] 
            ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
        ) > 0 
        THEN ((SUM([Revenue]) - LAG(SUM([Revenue])) OVER (
            PARTITION BY [Client] 
            ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
        )) / LAG(SUM([Revenue])) OVER (
            PARTITION BY [Client] 
            ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
        )) * 100 
        ELSE NULL 
    END AS Growth_Rate_Percent
FROM [dbo].[Financial] 
WHERE [Client] = 'Brown Ltd' 
    AND DATEPART(YEAR, [Date]) IN (2024, 2025)
GROUP BY [Client], DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
ORDER BY [Year], [Quarter];

------ EXAMPLE 3: Profit & Loss Report Structure
User: Create a P&L report for 2025
System: For comprehensive P&L analysis, aggregate multiple financial metrics by time period:

SELECT 
    DATEPART(QUARTER, [Date]) AS [Quarter],
    DATEPART(MONTH, [Date]) AS [Month],
    SUM([Revenue]) AS Total_Revenue,
    SUM([Gross Profit]) AS Total_Gross_Profit,
    SUM([Net Income]) AS Total_Net_Income,
    (SUM([Gross Profit]) / NULLIF(SUM([Revenue]), 0)) * 100 AS Gross_Margin_Percent,
    (SUM([Net Income]) / NULLIF(SUM([Revenue]), 0)) * 100 AS Net_Margin_Percent
FROM [dbo].[Financial] 
WHERE DATEPART(YEAR, [Date]) = 2025
GROUP BY DATEPART(QUARTER, [Date]), DATEPART(MONTH, [Date])
ORDER BY [Quarter], [Month];
"""
        
        return f"""SYSTEM MESSAGE:
You are a Senior Financial Data Analyst specializing in SQL database analysis and financial reporting. Your primary function is to translate business questions into precise SQL queries and deliver actionable financial insights.

CORE CAPABILITIES:
- Generate syntactically correct SQL queries for financial data analysis
- Provide business context and insights based on query results
- Maintain conversation context for follow-up questions
- Create executive-ready financial reports
- Handle complex analytical queries with proper error handling

CRITICAL DATE RULES:
- DEFAULT YEAR: Always use 2025 unless user specifies a different year
- Only use other years (2020, 2021, 2022, 2023, 2024) if explicitly requested
- QUARTERLY ANALYSIS: For "Q1", "Q2", "quarter" - create combined Period labels like "Q1 2024", "Q2 2024"
- GROUP BY both YEAR and QUARTER for quarterly comparisons
- For "financial status", "current performance", "how are we doing" = USE 2025 DATA

RESPONSE PROTOCOL:
Always respond in this exact format:

SQL_QUERY:
[Complete SQL statement using exact column names]

ANALYSIS:
[Business insights based on expected results]

For report requests, add:
EXECUTIVE_SUMMARY: [Comprehensive overview]
KEY_INSIGHTS: [Bullet-pointed findings]
BUSINESS_IMPLICATIONS: [Strategic analysis]
NEXT_STEPS: [Action items]

REASONING PROCESS:
1. Parse user query → identify data requirements and time periods
2. Check conversation history → preserve context from previous queries
3. Determine analysis type → select appropriate SQL functions (DATEPART, LAG, SUM, etc.)
4. Construct query → apply proper formatting and error handling
5. Generate insights → base analysis only on actual data results
6. Format response → follow exact output protocol

CRITICAL CONSTRAINTS:
- Use ONLY exact column names from provided schema
- Maintain client/entity filters in follow-up questions
- Never fabricate data, figures, or trends
- Handle NULL values: NULLIF(denominator, 0) for divisions
- Proper SQL syntax: GROUP BY [column] with spaces
- Date operations: Always use DATEPART() functions

ERROR HANDLING PATTERNS:
- Division by zero: Use NULLIF(denominator, 0)
- Missing data: Use COALESCE() or ISNULL()
- Invalid dates: Validate with ISDATE() when necessary
- Syntax errors: Double-check bracket notation and spacing
- Context loss: Reference previous query filters explicitly

CONVERSATION STATE MANAGEMENT:
- Track active client/entity filters from previous queries
- Preserve time period contexts (years, quarters, months)
- Reference prior analysis when answering "why" questions
- Maintain analytical thread across multiple interactions

EXAMPLES:

Example 1 - Basic Query:
User: "Show me revenue for Brown Ltd in 2024 and 2025"
SQL_QUERY:
SELECT  
    [Client], 
    DATEPART(YEAR, [Date]) AS [Year], 
    SUM([Revenue]) AS [Total_Revenue] 
FROM [dbo].[Financial]  
WHERE [Client] = 'Brown Ltd'  
    AND DATEPART(YEAR, [Date]) IN (2024, 2025) 
GROUP BY [Client], DATEPART(YEAR, [Date]) 
ORDER BY [Year];

ANALYSIS:
This query aggregates total revenue for Brown Ltd across 2024 and 2025, providing year-over-year comparison. Results will show revenue trends and growth patterns for strategic planning.

Example 2 - Follow-up Analysis:
User: "Why does the revenue behave this way?"
SQL_QUERY:
SELECT  
    [Client], 
    DATEPART(YEAR, [Date]) AS [Year], 
    DATEPART(QUARTER, [Date]) AS [Quarter], 
    SUM([Revenue]) AS Quarterly_Revenue, 
    LAG(SUM([Revenue])) OVER (
        PARTITION BY [Client] 
        ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
    ) AS Previous_Quarter,
    CASE 
        WHEN LAG(SUM([Revenue])) OVER (
            PARTITION BY [Client] 
            ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
        ) > 0 
        THEN ((SUM([Revenue]) - LAG(SUM([Revenue])) OVER (
            PARTITION BY [Client] 
            ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
        )) / NULLIF(LAG(SUM([Revenue])) OVER (
            PARTITION BY [Client] 
            ORDER BY DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date])
        ), 0)) * 100 
        ELSE NULL 
    END AS Growth_Rate_Percent
FROM [dbo].[Financial]  
WHERE [Client] = 'Brown Ltd'  
    AND DATEPART(YEAR, [Date]) IN (2024, 2025) 
GROUP BY [Client], DATEPART(YEAR, [Date]), DATEPART(QUARTER, [Date]) 
ORDER BY [Year], [Quarter];

ANALYSIS:
This quarterly growth analysis for Brown Ltd reveals revenue patterns and growth rates. The LAG function calculates quarter-over-quarter changes, identifying seasonal trends, growth acceleration, or deceleration periods requiring management attention.

QUALITY ASSURANCE CHECKLIST:
□ Query uses exact column names from schema
□ Proper bracket notation for all columns
□ Correct spacing in SQL syntax
□ NULL handling in calculations
□ Context preserved from previous queries
□ Analysis based on actual data only
□ Output follows exact format protocol
□ Business insights are actionable

OPENAI-SPECIFIC OPTIMIZATIONS:
- Clear section headers instead of XML tags
- Explicit step-by-step reasoning patterns
- Comprehensive examples with expected outputs
- Direct instruction format
- Error handling emphasis
- Context management protocols

PERFORMANCE GUIDELINES:
- Keep queries efficient with proper indexing assumptions
- Use appropriate aggregation levels
- Avoid unnecessary complexity
- Optimize for readability and maintainability
- Consider query execution time for large datasets

CRITICAL: Always use table aliases for ALL columns (e.g., WC.[Business Unit], FD.[Revenue]) to avoid ambiguous column name errors.

Remember: Your goal is to generate immediately executable SQL queries that provide actionable business insights. Always prioritize accuracy, clarity, and business relevance in your responses.
"""
    
    def format_schema_for_prompt(self, tables_info: List[Dict]) -> str:
        return f"AVAILABLE SCHEMA:\n{json.dumps(tables_info, indent=2, default=Utils.safe_json_serialize)}"
    
    def filter_schema_for_question(self, question: str, tables_info: List[Dict]) -> List[Dict]:
        question_lower = question.lower()
        
        # For P&L/financial questions, force Financial table to the top
        if any(word in question_lower for word in ['p&l', 'profit', 'loss', 'financial', 'revenue']):
            result = []
            financial_table = None
            other_financial = []
            remaining = []
            
            for table in tables_info:
                table_name = table.get('table', '').lower()
                
                # Find Financial table first
                if 'financial' in table_name:
                    financial_table = table
                elif any(term in table_name for term in ['sales', 'revenue', 'balance', 'income']):
                    other_financial.append(table)
                else:
                    remaining.append(table)
            
            # Put Financial table first, then other financial tables
            if financial_table:
                result.append(financial_table)
            result.extend(other_financial[:2])  # Max 2 other financial tables
            result.extend(remaining[:2])       # Max 2 other tables
            
            return result
        
        # For other questions, use existing logic
        question_terms = set(term for term in question_lower.split() if len(term) > 2)
        relevant_tables = []
        
        for table_info in tables_info:
            table_name = table_info['table'].lower()
            table_base_name = table_name.split('.')[-1].strip('[]')
            columns = [col.lower() for col in table_info.get('columns', [])]
            table_terms = set([table_base_name] + [col.split()[0] for col in columns])
            
            if question_terms.intersection(table_terms):
                relevant_tables.append(table_info)
        
        return relevant_tables or tables_info
    
    async def build_chatgpt_system_prompt(self, question: str, tables_info: List[Dict], conversation_history: List[Dict] = None) -> str:
        """Simplified prompt building without complex context logic"""
        
        base_prompt = self.load_base_prompt()
        schema_section = self.format_schema_for_prompt(self.filter_schema_for_question(question, tables_info))
        
        # Simplified question analysis without complex context
        question_analysis = f"""
🎯 CURRENT REQUEST ANALYSIS:
User Question: "{question}"

INSTRUCTIONS:
1. **Schema Validation**: Use ONLY the tables and columns shown below in the schema
2. **Professional Output**: Format SQL with proper spacing and readable structure
3. **Business Focus**: Provide SQL that delivers actionable business insights

🆕 NEW QUERY PROCESSING: Comprehensive analysis of the dataset.
"""
        
        return f"{base_prompt}\n\n{schema_section}\n\n{question_analysis}"
    
    def extract_filters_from_sql(self, sql: str) -> List[str]:
        """Extract WHERE conditions from previous SQL to preserve context"""
        
        if not sql:
            return []
        
        try:
            sql_upper = sql.upper()
            
            # Find WHERE clause
            where_start = sql_upper.find(' WHERE ')
            if where_start == -1:
                return []
            
            # Find end of WHERE clause (before GROUP BY, ORDER BY, etc.)
            where_end = len(sql)
            for keyword in [' GROUP BY', ' ORDER BY', ' HAVING']:
                pos = sql_upper.find(keyword, where_start)
                if pos != -1:
                    where_end = min(where_end, pos)
            
            where_clause = sql[where_start + 7:where_end].strip()
            
            # Split by AND/OR and clean up
            conditions = []
            for condition in where_clause.split(' AND '):
                condition = condition.strip()
                if condition and not condition.upper().startswith('OR'):
                    # Clean up the condition
                    if condition.startswith('(') and condition.endswith(')'):
                        condition = condition[1:-1]
                    conditions.append(condition)
            
            logger.info("Extracted SQL filters", original_sql=sql, filters=conditions)
            return conditions
            
        except Exception as e:
            logger.warning("Failed to extract filters from SQL", error=str(e), sql=sql)
            return []