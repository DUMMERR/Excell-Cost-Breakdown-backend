# Excel processor API backend 
### This is a temporary read me placeholder while a proper readMe.md gets established
**Dependency licenses and direct links to their Github page can be found withing DependencyLicenses.txt
  Only top level dependencies have been linked**



  

The Cost Break Down backend is meant to be used in order to process excel files with operating costs per time period in mind such as vendors , prices etc.

The backed API endpoint takes the excel files , and using pandas and a sequence Matcher (external library) to derive meaning from the headers , finds the best possible match for a spend column and vendor column it can find in order to automate the search process for the user and uses those to create and return an array with objects containing the name and spend - value , spending is cumulative so if multiple rows pertaining to one company exist the array returns 1 object for that company with the total of the money spent on that vendor.

**An example of such an excel file would be**

| Date | Transaction Id  | Vendor |  Cost | Currency |
|---|---|---|---|---|
|  01/06 | 1  | SomeName.Inc |  4090 |  JYN |
|  01/06 | 2  | Company  | 230 | USD  |
|  04/06 | 3  | Technology and Sons  | 389  | EUR  |



**Example of a returned Json obj:**
```json
	{
		"normalization_base": "EUR",      		//All data is normalised to euro for conversions
		"conversion_matrices":{		  		//Returns a conversion matrice , details bellow
			"EUR": {							//Currency code as a key for conversion rates
		      "rate_against_eur": 1,
		    },
		    "JPY": {
		      "rate_against_eur": 185.3,
		      "is_user_default": true			//Can be used to show the values in the selected Currency
		    },
		    "USD": {
		      "rate_against_eur": 1.1567,
		    }
		},
		"file_batch_data":[			//Data returned per file the user has uploaded each one as an object
				{
      			"file_name": "Test_File.xlsx",   //The file name 
				"file_status": "success",		//Indicates if anything went wrong
				"failed_rows_count": 0,    	//How many rows failed to read
				"failed_rows_details":[], //returns an array of what row failed and why
				"expense_data": [            //The array containing all the objects with the name and spend
					{
						"company": "SomeName.Inc",
						"value": 22.14
					},
					{
						"company": "Company",
						"value": 199.92
					},
					{
						"company": "Technology and Sons",
						"value": 389  
					}
				]
			}
		]
	}
```

The backend itself is set to get updates with live ECBU exchange rate through their API every day at 16:30 (4:30 PM), while the ECBU exchange rates themselves gets updated every day at 16 (4 PM), times are in Central European Time.
