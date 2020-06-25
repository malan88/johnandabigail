build:
	zip -r lambda.zip * -x __pycache__ .git .gitignore
deploy:
	aws lambda update-function-code --function-name john-and-abigail --zip-file fileb://lambda.zip
