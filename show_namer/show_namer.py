import re
import os
import sys
import traceback
import requests
from Tkinter import *
import tkFileDialog

# http://www.epguides.com/greysanatomy/
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
		if (self.number != '' and self.season != '' and self.extension != '' and self.filepath != '' and self.correctedName != '' and self.showName != ''):
			newName = self.justPath + '\\' + self.showName + ' S' + self.season + 'E' + self.number + ' - ' + self.correctedName + '.' + self.extension
			os.rename(self.filepath, newName)
			print('..renamed ' + self.filepath + ' to ' + newName)
		else:
			print('Failed file: ')
			print('Season: ' + self.season + '    Episode: ' + self.number)
			print('Extension: ' + self.extension + '    Filepath: ' + self.filepath)
			print('New Name: ' + self.correctedName + '    Show Name: ' + self.showName)

class ShowRenamer:
	episodes = {}
	episode_season_patterns = [re.compile('Season (\d{1,2})'), re.compile('(\d{1,2})[eExX.](\d{1,2})')]
	line_pattern = re.compile('\d+[.]? +(\d+-\d+) +.{12,16} \d+ \w+ \d\d +(?:<.*?>)(.+?)</a>')
	episode_number_patterns = [re.compile('\d[eExX.](\d{1,2})'), re.compile('[^0-9](\d{1,2})[^0-9]'), re.compile('[^0-9](\d{3,4})[^0-9]')]
	directory = ''

	def __init__ (self, root):
		self.root = root
		self.pack_frame()
		self.draw_interfaces()

	def pack_frame(self):
		frame = Frame(root)
		frame.pack()
		self.frame = frame

	def draw_interfaces(self):
		# Episode Guide URL interface
		self.urlVar = StringVar()
		Label(self.frame, text='Episode Guide URL').grid(row=0, column=0, padx=10, pady=10)
		urlEntry = Entry(self.frame, textvariable=self.urlVar)
		urlEntry['width'] = 50
		urlEntry.grid(row=0, column=1, padx=10, pady=10)

		# Show Name interface
		self.showNameVar = StringVar()
		Label(self.frame, text='Show Name').grid(row=1, column=0, padx=10, pady=10)
		showNameEntry = Entry(self.frame, textvariable=self.showNameVar)
		showNameEntry['width'] = 50
		showNameEntry.grid(row=1, column=1, padx=10, pady=10)

		# Select Show and Rename buttons
		b = Button(self.frame, text='Select Show', command=self.get_folder)
		b.grid(row=2, column=0, padx=10, pady=10)
		b = Button(self.frame, text='Rename', command=self.rename_show)
		b.grid(row=2, column=1, padx=10, pady=10)

	def get_folder(self):
		dirname = tkFileDialog.askdirectory(parent=self.root,title='Please select a directory')
		self.fullDir = dirname
		self.directory = dirname.split('/')[-1]
		self.urlVar.set('http://epguides.com/' + self.directory.replace(' ', '').replace('\'', '') + '/')
		self.showNameVar.set(self.directory)

	def create_episode_model(self, episode_season, episode_number, fullpath, extension):
		if episode_season == '' or episode_number == '':
			# Skip silently for now. This is currently an okay outcome.
			return

		newEpisode = Episode()

		# Update episode and season numbers to be 2 digit
		newEpisode.season = self.zero_pad(episode_season)
		newEpisode.number = self.zero_pad(episode_number)
		newEpisode.extension = extension
		newEpisode.filepath = fullpath
		newEpisode.correctedFilename = ''
		newEpisode.justPath = '\\'.join(fullpath.split('\\')[0:-1])
		newEpisode.showName = self.showNameVar.get()

		# Add the episode to our internal episode list.
		episode_id = self.get_episode_id(newEpisode.season, newEpisode.number)
		self.episodes[episode_id] = newEpisode
		print('..added new episode: ' + fullpath + ' under ' + episode_id)

	# Try using regex to get season number. We may get lucky and get the episode number as well.
	# We need to do this because people use a wide variety of naming patterns.
	def interpret_episode_season(self, name, fullpath):
		episode_season = ''
		episode_number = ''
		for pattern in self.episode_season_patterns:
			pattern_result = pattern.findall(fullpath)
			if len(pattern_result) > 0: # If the regex leads us directly to a the season, use it
				if isinstance(pattern_result[0], basestring):
					episode_season = pattern_result[0]
					break
				elif isinstance(pattern_result[0], (list, tuple)): # Sometimes the season will be matched up with an episode number
					episode_season = pattern_result[0][0]
					if len(pattern_result) > 1:
						episode_number = pattern_result[0][1]
		return (episode_season, episode_number)

	# Try using regex to get episode number. We may get lucky and get the season number as well.
	# We need to do this because people use a wide variety of naming patterns.
	def interpret_episode_number(self, name, episode_season):
		episode_number = ''
		for pattern in self.episode_number_patterns:
			pattern_result = pattern.findall(name)
			if len(pattern_result) > 0:
				episode_number = pattern_result[0]
				if len(episode_number) > 3: # If we got a 3+ digit match, then we should get season here too
					episode_number = match[-2:]
					episode_season = match[0:-2]
				break
		return (episode_season, episode_number)

	def ingest_local_files(self):
		#make a list of video objects in this directory, and figure out their season.
		print('started walking directories')
		for root, dirs, files in os.walk(self.fullDir):
			for name in files:
				extension = name.split('.')[-1]
				if extension in ('mpeg', 'mp4', 'avi', 'mkv', 'mov', 'mpg'):
					fullpath = os.path.join(root, name).replace('/', '\\')
					name = name.split('\\')[-1] #get only the last piece of the name, since it has path info.

					# We could potentially season or number while trying to get the other one.
					episode_season, episode_number = self.interpret_episode_season(name, fullpath);
					if episode_number == '':
						episode_season, episode_number = self.interpret_episode_number(name, episode_season);
					print ('season: ' + episode_season + ' number: ' + episode_number)
					self.create_episode_model(episode_season, episode_number, fullpath, extension)

		print('done walking directories.')

	def get_episode_guide_html(self):
		print('starting http request.')
		#get list of episode names, and attept to attach them to objects.
		html = requests.get(self.urlVar.get()).text

		#html = str(html, encoding='utf8')
		print('finished http request.')
		return html

	def parse_html_request(self, html):
		print('starting parsing http request.')
		for line in html.split('\n'):
			line = line.replace('\u2019', '\'')
			match = self.line_pattern.search(line)
			if match:
				episode_season, episode_number = match.group(1).split('-')

				episode_season = self.zero_pad(episode_season)
				episode_number = self.zero_pad(episode_number)
				episode_id = self.get_episode_id(episode_season, episode_number)

				episode_name = match.group(2).replace('?', '').replace(':', '-')

				if episode_id in self.episodes:
					print('Found name for episode ' + episode_id + ': ' + episode_name)
					self.episodes[episode_id].correctedName = episode_name.replace('/', '-').replace(':', '-')
		print('finished parsing http request.')

	def get_episode_id(self, episode_season, episode_number):
		return episode_season + 'x' + episode_number

	def rename_local_files(self):
		print('starting renaming.')
		for episodeKey in self.episodes:
			self.episodes[episodeKey].rename()
		print('finished renaming.')

	def rename_show(self):
		self.ingest_local_files()
		html = self.get_episode_guide_html()
		self.parse_html_request(html)
		self.rename_local_files()

	def zero_pad(self, string):
		return '{:0>2}'.format(string)

try:
	root = Tk()
	root.title = 'Show Renamer'
	app = ShowRenamer(root)
	root.mainloop()
except:
	exc_type, exc_value, exc_tb = sys.exc_info()
	errors = traceback.format_exception(exc_type, exc_value, exc_tb)
	for line in errors:
		print(line)