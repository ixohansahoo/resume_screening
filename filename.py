import os
FOLDER_PATH=r'C:\Users\ASUS\Desktop\New folder (2)\static\files'
def list(dir):
    filenames=os.listdir(dir)
    for filenames in filenames:
        print("filename"+filenames)
if __name__=='__main__':
    list(FOLDER_PATH)