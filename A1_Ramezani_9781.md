# Assignment 1 – Status Report  
Name: Aiden Ramezani  
Student ID: 123456789  
Group: 4


| Function Name              | Status     | What’s Missing/Buggy                                     |
|----------------------------|------------|----------------------------------------------------------|
| add_book_to_catalog        | Partial    | ISBN validation is incomplete (Server Side): allows non-digit characters in ISBN; no    explicit None/blank guard before len() check. |
| book_catalog_display       | Complete   | Works as expected, no issues found |
| borrow_book                | Partial    | Borrow limit uses `> 5` instead of `>= 5` (allows a 6th book). |
| process_return             | Missing    | Not implemented. Must verify patron borrowed the book, set return_date, update copies, and calculate/display late fees (R4).          |
| calculate_late_fee         | Missing    | Not implemented. Must implement 14-day due, 0.50/day first 7 overdue, 1.00/day after, max $15 (R5). |
| search_books               | Missing    | Not implemented. Must support q + type (title/author/isbn), partial & case-insensitive for title/author, exact for ISBN (R6).         |
| patron_status_report       | Missing    | Not implemented. Must show current borrows + due dates, total late fees, count borrowed, and history; add menu option (R7).           |


