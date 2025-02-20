# Guidance Prompt For AI

 The purpose of this application is to provide a convenient and fast interface for reading and writing NFC tags. 

 The particular use case is that I use NFC tags in order to record inventory labels. Each inventory label is a digital link IE URL.

 This is an example URL from the inventory system. As you can see, they are quite long:

 https://inventory.example.com/item/8ebf2dfe-507f-44a5-acfc-b94d895f1975

 Whenever I create tags, I create and lock them simultaneously. I use predominantly ntag 2 and 3, although I'd like this to work with different tags if possible. I currently use the ACR1252U but also have another ACr NFC tag reader and writer.

 Currently the app has a few essential functionalities: When it reads tags, it automatically opens them in a browser. This is intentional and facilitates being able to quickly bring a item in my inventory up to the NFC reader and have it quickly open the catalog page in the browser. The right page contains a basic and functional interface for writing individual tags and also doing so in a batch, which is sometimes a requirement. 

 The tags should only contain the URL and no other data. 

 The design is basic and functional although it could use a bit of polish.

 Your objective:

Thinking within the confines of these requirements, suggest any additilonal fucntionalitiesi or UI/UX improvements which you think would support the operation of this app. 

Then, implement them. 
