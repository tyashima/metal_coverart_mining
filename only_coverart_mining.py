import urllib2
import os
import urllib
from bs4 import BeautifulSoup
import numpy as np
import json
import scipy
import scipy.misc
import pdb
import re
import sys
import argparse

# input.txt should be like
# Anthrax,0,Thrash 0 means all
# Sepultura,1-4,Thrash,5-,Groove

def choose_band(url):
	try:
		fp = urllib2.urlopen(url)
		html = fp.read()
		fp.close()

		if "may refer to" in html:	#if multiple candidates found
			soup = BeautifulSoup(html)
			bandlinks = [a.get("href") for a in soup.find_all("a") if "/bands/" in str(a)]
			prop_url = bandlinks[0]
		else:
			prop_url = url
		error_flag = 0

	except urllib2.URLError:
		error_flag = 1
		prop_url = "http://www.fake"

	return prop_url, error_flag


def discography_search(bandname, url, error_flag, failed_data, line):
	url_disc = "http://www.fake"

	if error_flag == 0:
		try:
			fp = urllib2.urlopen(url)
			html = fp.read()
			fp.close()
			soup = BeautifulSoup(html)

			link_all = soup.find_all(href=re.compile("discography"))
			for link in link_all:
				if str(link.string) == 'Complete discography':
					next_link = link
					url_disc = next_link.get("href")
					break

		except urllib2.URLError:
			print "Couldn't find the database for %s." % bandname.split("/")[0]
			error_flag = 1

		except:
			print "Unexpected Error for %s. No Discography?" % bandname.split("/")[0]
			error_flag = 1
	else:
		print "Error:Couldn't find the band info."
		failed_data += line
		error_flag = 1

	return url_disc, error_flag, failed_data


def access_album_rec(url_disc, bandname, target):
	fp = urllib2.urlopen(url_disc)
	html = fp.read()
	fp.close()
	soup = BeautifulSoup(html)

	target_links, links_all = list(), list()
	links_all.extend(soup.find_all(class_="album"))
	links_all.extend(soup.find_all(class_="other"))

	for n in xrange(len(links_all) / 3):
		if links_all[3 * n + 1].get_text() in target:
			target_links.append(links_all[3 * n].get("href"))

	num_album = len(target_links)

	return target_links, num_album


def choose_proper_link(link, bandname):
	fp = urllib2.urlopen(link)
	html = fp.read()
	fp.close()

	soup = BeautifulSoup(html)
	fmt = soup.find("dt", text="Format:").find_next().get_text()
	imgid = str(soup.find("a", class_="image"))
	if ("CD" in fmt or "vinyl" in fmt or "Digital" in fmt) and 'id="cover"' in imgid:
		p_link = link
	else:
		p_link = "dammy"
		links = soup.find("a",text="Other versions")
		if links is None:
			print "No CD or Vinyl found for %s" % link[37 + len(bandname.split("/")[0]) + 1:]
		else:
			fp = urllib2.urlopen(links.get("href"))
			html = fp.read()
			fp.close()
			soup_cand = BeautifulSoup(html)

			table = soup_cand.find_all("table")[0]
			rows = table.find_all("tr")[2:]
			row_elms = [row.find_all("td") for row in rows]
			format_list = [r[3].get_text() for r in row_elms]
			cd_vin_ind = np.where([l in ['CD', '12" vinyl', 'Digital', '7" vinyl'] for l in format_list])[0]

			if len(cd_vin_ind) != 0:
				all_links = np.array([l.get("href") for l in soup_cand.find_all(href=re.compile("albums"))[1:]])[cd_vin_ind]

				for link_cand in all_links.tolist():
					fp = urllib2.urlopen(link_cand)
					html = fp.read()
					fp.close()
					soup = BeautifulSoup(html)
					if 'id="cover"' in str(soup.find("a", class_="image").get_text):
						p_link = link_cand
						break
					else:
						continue
			else:
				print "CD or Vinyl eddition not found" # never happens

	return p_link, soup



def get_album_titles(links, bandname):
	imgurls, titles, failed_set = list(), list(), set()

	for link in links:
		p_link, soup = choose_proper_link(link, bandname)
		if not p_link == "dammy":	# img exits
			imgsrc = soup.find("a", class_="image")
			imgurl = imgsrc.get("href")
			imgurls.append(imgurl)
			title = imgsrc.get("title")
			title = re.sub(r'[- *:/\\|?]', '_', title)
			title = title.replace("___", "_")
			titles.append(title)
		else:
			imgurls.append(links.index(link))
			titles.append("dammy")
			failed_set.add(links.index(link))

	return imgurls, titles, failed_set


def download(imgurl, bandname, title, num_cand, imgurls, store_dir):
	if imgurl != imgurls.index(imgurl) and type(imgurl) is not int:
		img = urllib.urlopen(imgurl)
		path = store_dir + "imgs/" + title + ".jpg"

		localfile = open(path, 'wb')
		localfile.write(img.read())
		img.close()
		localfile.close()
		im = scipy.misc.imread(path)
		os.remove(path)

		if len(im.shape) != 3 or ((im.shape[0] / float(im.shape[1])) > 1.4) or ((im.shape[0] / float(im.shape[1])) < 0.7) or im.shape[2] != 3:
			#print "%s has some problems. Not square or monochrome." % title
			im2 = imgurls.index(imgurl)
		else:
			im2 = scipy.misc.imresize(im, [128, 128])
			im2 = np.array(im2)
			scipy.misc.imsave(path, im2)
			sys.stdout.write("\r\t\t\t\t\t\t\t\t\t\t\t\t\t\t")
			sys.stdout.write("\r%s worked!                  " % title)
			sys.stdout.flush()
	else:
		im2 = imgurls.index(imgurl)

	return im2



def main(params):
	store_dir = params["imgdir"]

	if not os.path.isdir(store_dir + "imgs"):
		os.mkdir(store_dir + "imgs")


	target = ["Full-length"]
	if params['Single'] is True:
		target.append("Single")

	if params['EP'] is True:
		target.append("EP")

	if params['Live'] is True:
		target.append("Live album")


	worked_data = ""	# stored as string
	failed_data = ""	# stored as string

	with open("input_t.txt", 'r') as f:
		line = f.readline()

		while line:
			error_flag = 0
			bandname = line.split(",")[0]
			url = "http://www.metal-archives.com/bands/" + bandname
			print "Processing %s..." % bandname.split("/")[0]

			try:
				proper_url, error_flag = choose_band(url)
				url_disc, error_flag, failed_data = discography_search(bandname, proper_url, error_flag, failed_data, line)
				target_links, num_album = access_album_rec(url_disc, bandname, target)

				if num_album == 0:
					"Skipped %s. Error detected." % bandname.split("/")[0]
					failed_data += line
					error_flag = 1
					line = f.readline()
					continue

				imgurls, titles, failed_record_set = get_album_titles(target_links, bandname)
				#pdb.set_trace()
				cover_imgs = [download(imgurls[j], bandname, titles[j], num_album, imgurls, store_dir) for j in xrange(len(imgurls))]
				failed_img_set = set([x for x in cover_imgs if type(x) is int])

				failed_img_set.update(failed_record_set)

				if error_flag == 0:
					worked_data += line
					print "%s finished." % bandname.split("/")[0]
				else:
					failed_data += line
			except:
				"Skipped %s. Error detected." % bandname.split("/")[0]

			line = f.readline()

	with open("input_t.txt", 'w') as f_new:	# overwrites the input file
		line = f_new.write(worked_data)




if __name__ == "__main__":
	parser = argparse.ArgumentParser()

	# input json
	parser.add_argument('--imgdir', dest="imgdir", default="", help='where to store downloaded coverart images')
	parser.add_argument('--single', dest="Single", default=False, type=bool, help='Include Singles?')
	parser.add_argument('--EP', dest="EP", default=False, type=bool, help='Include EPs?')
	parser.add_argument('--Live', dest="Live", default=False, type=bool, help='Include Live Albums?')

	args = parser.parse_args()
	params = vars(args) # convert to ordinary dict
	print 'parsed input parameters:'
	print json.dumps(params, indent = 2)
	main(params)
