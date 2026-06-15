# Excell processor endpoint

This is a temporary read me placeholder while a proper readMe.md gets established

Dependency licenses and direct links to their github page can be found withing DependencyLicenses.txt


The Cost Break Down backend is meant to be used in order to process excell files with costological items in mind such as vendors , prices etc etc.
The backed api endpoint takes the excell files and using pandas and a sequence Matcher (external library) to derieve meaning from the headers , finds the best possible match for a spend column and vendor column it can find in order to automate the search process for the user and uses those to create and return a dictionary with key value pairs of the company name as the key and a value being their spending , spending is cumulative so if multiple rows pertaining to one company exist the dictionary returns 1 entry for that company with ther total of the money spend on that vendor
The app gets updates with live ecbu rate requests every day at 16:30 (4:30 PM), while the ecbu rate itself gets updated every day at 16 (4 PM), times are in Central European Time.
