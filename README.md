# physics_lab_report_generator

Small script to take a PDF file (for my physics lab), extract the introduction, summarize it, then make a rough outline of the lab report, save it as a .txt, and lastly upload it to my google drive as a google doc so I can finish the rest of the report manually.

Running this script before doing every lab should honestly save like 10-15 minutes in total.

In summary, this script does all the work you cant automate in a lab. Automating doing the lab would be a waste of time since you typically change software every week or two.

## More detailed description

The file automatically makes: headers (Name,date,lab #, rough title (pdf name))

Then it makes the introduction (just pastes the summary). You can use a paraphrase tool to restructure the intro

Creates a space for the Data and Analysis Section

Lists the number of questions you need to solve (might be more than actually needed since regex is sometimes bad in python)

Lastly, it provides an outline for the conclusion

## Why put this on github?

I think it shows recruiters the amount of work I'll do to do as little work as possible (which is a good thing in CS in my opinion).

I have other scripts like this that help me with other course work and a script that automatically applies to jobs for me on Indeed.
