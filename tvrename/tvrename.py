import re
import os
import sys
import traceback
import urllib.request
from tkinter import *
from tkinter import filedialog

class Episode:
	def __init__ (self):
		self.number = ''
		self.season = ''
		self.extension = ''
		self.filepath = ''
		self.correctedName = ''
		self.justPath = ''
		self.showName = ''
	
	def rename(self):
		if not (self.number + self.season + self.extension + self.filepath + self.correctedName + self.showName == ''):
			newName = self.justPath + '\\' + self.showName + ' S' + self.season + 'E' + self.number + ' - ' + self.correctedName + '.' + self.extension
			os.rename(self.filepath, newName)
			print("..renamed " + self.filepath + " to " + newName)
		else:
			print('Failed file: ')
			print('Season: ' + self.season + '    Episode: ' + self.number)
			print('Extension: ' + self.extension + '    Filepath: ' + self.filepath)
			print('New Name: ' + self.correctedName + '    Show Name: ' + self.showName)

class ShowRenamer:
	def __init__ (self, root):
		self.root = root
		self.episodes = {}
		
		self.season_pattern_a = re.compile("Season (\d{1,2})")
		self.season_pattern_b = re.compile("(\d{1,2})[eExX.](\d{1,2})")
		self.lineExp = re.compile("\d+ +(\d+-\d+) .{12,16} .\d/\w\w\w\/\d\d +(?:<.*?>)(.+?)</a>")
		self.number_pattern_a = re.compile("\d[eExX.](\d{1,2})")
		self.number_pattern_b = re.compile("[^0-9](\d{1,2})[^0-9]")
		self.number_pattern_c = re.compile("[^0-9](\d{3,4})[^0-9]")
		#self.seasonExp = re.compile("&bull; Season (\d*)")
		
		frame = Frame(root)
		frame.pack()
		self.frame = frame
		
		self.directory = ''

		self.urlVar = StringVar()
		Label(frame, text="Episode Guide URL").grid(row=0, column=0, padx=10, pady=10)
		urlEntry = Entry(frame, textvariable=self.urlVar)
		urlEntry["width"] = 50
		urlEntry.grid(row=0, column=1, padx=10, pady=10)
		
		self.showNameVar = StringVar()
		Label(frame, text="Show Name").grid(row=1, column=0, padx=10, pady=10)
		showNameEntry = Entry(frame, textvariable=self.showNameVar)
		showNameEntry["width"] = 50
		showNameEntry.grid(row=1, column=1, padx=10, pady=10)
		
		#urlEntry.get()
		
		b = Button(frame, text="Select Show", command=self.getFolder)
		b.grid(row=2, column=0, padx=10, pady=10)
		b = Button(frame, text="Rename", command=self.rename_show)
		b.grid(row=2, column=1, padx=10, pady=10)
		
	def getFolder (self):
		dirname = filedialog.askdirectory(parent=self.root,title='Please select a directory')
		self.fullDir = dirname
		self.directory = dirname.split('/')[-1]
		self.urlVar.set("http://epguides.com/" + self.directory.replace( " ", "").replace( "'", "") + "/")
		self.showNameVar.set(self.directory)
	
	def rename_show(self):
		#make a list of video objects in this directory, and figure out their season.
		print("started walking directories")
		for root, dirs, files in os.walk(self.fullDir):
			for name in files: 
				extension = name.split('.')[-1]
				if extension in ('mpeg', 'mp4', 'avi', 'mkv', 'mov'):
					fullpath = os.path.join(root, name).replace("/", "\\")
					name = name.split('\\')[-1] #get only the last piece of the name, since it has path info.
					season = "-1"
					number = "-1"
					pattern_result = self.season_pattern_a.findall(fullpath)
					if len(pattern_result) > 0:
						season = pattern_result[0]
					else:
						pattern_result = self.season_pattern_b.findall(name)
						if len(pattern_result) > 0:
							season = pattern_result[0][0]
							if len(pattern_result) > 1:
								number = pattern_result[0][1]
					if season != "-1":
						if not number != "-1":
							pattern_result = self.number_pattern_a.findall(name)
							if len(pattern_result) > 0:
								number = pattern_result[0]
							else:
								pattern_result = self.number_pattern_b.findall(name)
								if len(pattern_result) > 0:
									number = pattern_result[0]
								else:
									pattern_result = self.number_pattern_c.findall(name)
									if len(pattern_result) > 0:
										match = pattern_result[0]
										number = match[-2:]
										season = match[0:-2]
						if number != "-1":
							newEpisode = Episode()
							if len(season) == 1:
								season = '0' + season
							newEpisode.season = season
							if len(number) == 1:
								number = '0' + number
							newEpisode.number = number
							newEpisode.extension = extension
							newEpisode.filepath = fullpath
							newEpisode.correctedFilename = ''
							newEpisode.justPath = "\\".join(fullpath.split('\\')[0:-1])
							newEpisode.showName = self.showNameVar.get()
							self.episodes[season + 'x' + number] = newEpisode
							print ("..added new episode: " + fullpath + ' under ' + season + 'x' + number)
		
		print ("done walking directories.")
		
		print ("starting http request.")
		#get list of episode names, and attept to attach them to objects.
		html = urllib.request.urlopen(self.urlVar.get()).read()
		html = str(html, encoding='utf8')
		print ("finished http request.")
		
		print ("starting parsing http request.")
		for line in html.split('\n'):
			line = line.replace("\u2019", "'")
			result2 = self.lineExp.search(line)
			if result2:
				epSeason, epNum = result2.group(1).split("-")
				if len(epSeason) == 1:
					epSeason = "0" + epSeason
				if len(epNum) == 1:
					epNum = "0" + epNum
				epName = result2.group(2).replace("?", "").replace(":", "-")
				if epSeason + 'x' + epNum in self.episodes:
					print ("EpName: " + epName)
					self.episodes[epSeason + 'x' + epNum].correctedName = epName.replace('/', '-').replace(':', '-')
		print ("finished parsing http request.")

		print ("starting renaming.")
		for episodeKey in self.episodes:
			self.episodes[episodeKey].rename()
		print ("finished renaming.")

try:
	root = Tk()
	root.title = "Corin's Show Renamer"
	app = ShowRenamer(root)
	root.mainloop()
except:
	exc_type, exc_value, exc_tb = sys.exc_info()
	errors = traceback.format_exception(exc_type, exc_value, exc_tb)
	for line in errors:
		print(line)