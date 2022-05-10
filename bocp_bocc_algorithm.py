# -*- coding: utf-8 -*-
"""BOCP_BOCC Algorithm

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HNZ3PIp4HeIjfyfzUBYWqt_NL40rMsis

# **Import drive**
"""

from google.colab import drive
drive.mount('/content/gdrive')

"""# **Librerie**"""

import glob
import xml.etree.ElementTree as ET
from collections import defaultdict
import re
import PIL
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter
import itertools
import math 
import pickle

"""# **Returns a list containing all GUI names**"""

#function to take all GUI's
def getGUIS(path):
  data = []
  for filename in os.listdir(path):
      if filename.endswith("uix"): 
        #delete last 4 characters for the file type
          Remove_last = filename[:len(filename)-4]
          data.append(path+"/"+Remove_last)
  return data

"""# **Returns a list containing all the components of a snapshot**"""

#function to take the components and each time opens all the components
def getComponents(elem,lista): 
    for child in elem.findall('*'):
      lista.append(child.items())
      getComponents(child,lista)
#create a list to get all components and call the getComponents function
def getComponentsFromSnapshot(elem):
  lista=[]
  getComponents(elem,lista)
  return lista

"""# **Returns the rgb value of the image's pixels**"""

#funzion to take the rgb value of the image's pixels
def getColor(S,x,y):
  return S.getpixel((x,y))

"""# **Return a dataframe of pixel components**"""

#takes as input a screenshot, the component, the type to each pixel assign a priority based on the hierarchy of the GUI, the color and the component itself
def getPixels(S,c, tipo):
  #takes ranges based on type and split it
  values=re.findall(r'\d+',c[16][1])
  component=c[3][1]
  if tipo==1:
    values=re.findall(r'\d+',c[17][1])
    component=c[4][1]
  print(values)
  asse_x_inizio=int(values[0])
  asse_y_inizio=int(values[1])
  asse_x_fine=int(values[2])
  asse_y_fine=int(values[3])

  result=[]
  list_color=[]
  list_x=[]
  list_y=[]
  list_component=[]
  #iterate x axis
  for x in range(asse_x_inizio,asse_x_fine):
    list_x.append(x)
  #iterate y axis
  for y in range(asse_y_inizio,asse_y_fine):
    list_y.append(y) 
  #makes the Cartesian product, takes all the colors according to the axes and assigns the component to the pixels
  for element in itertools.product(list_x,list_y):
    result.append(element)
    list_color.append(getColor(S,element[0],element[1]))
    list_component.append(component) 
  #dataframe creation
  pixel_c=pd.DataFrame(data=result)
  if list_color:
    pixel_c.columns = ['Axis-X', 'Axis-Y']
    pixel_c['R-G-B'] = list_color
    pixel_c["Components"] = component
  return pixel_c

"""# **Return Histogram of RGB values sorted by frequency**"""

#instead of using a histogram I preferred to use the Counter class to count the frequency of each color,
#sort the frequencies in descending order and return them in output
def getPixelHistogramSorted(pixel_c):
  if pixel_c:
    #count number of occurrence of value rgb
    count_element=Counter(pixel_c)
    #convert to dataframe, reset index and give new name columns
    df = pd.DataFrame.from_dict(count_element,orient='index').reset_index()
    df.columns =['R-G-B','N_occurrence']
    #sort df and return
    sorted_df=df.sort_values(by=['N_occurrence'], ascending=False)
    color_frequence=sorted_df['R-G-B'].values.tolist()
    return color_frequence

"""# **Return the color of Luminance**"""

#function of  T(level) of R-G-B
def TLevel(level):
  if level/255<=0.03928:
    return level/12.92
  else:
    value=(level+0.055)/(1.055)
    return (pow(value,2.4))
#funcion (a), relative luminance, that is based on the RGB color levels of a given color, with a level value in [1, 255] 
def getLuminanceByRGB(color):
  return 0.216*TLevel(color[0])+0.7152*TLevel(color[1])+0.0722*TLevel(color[2])
#funcion of the luminance-based contrast ratio Lum(a,b) that better accounts for differences between text and background color
def Lum(color,medoids):
  L_a=getLuminanceByRGB(color)
  L_b=getLuminanceByRGB(medoids)
  if L_a>L_b: return (L_a+0.05)/(L_b+0.05)
  else: return (L_b+0.05)/(L_a+0.05)

"""# **Return the metoids, a list of the most frequent color in a cluster**"""

#a medoid (as used in this article) is the most-frequent color in a cluster
def getMedoids(hist,k,r):
  medoids=[]
  if hist:
    medoids.append(hist[0])
    index=1
    medoidIndex=0
    while len(medoids)<k and index<len(hist):
      color=hist[index]
      if Lum(color,medoids[medoidIndex])>r:
        medoidIndex+=1
        medoids.append(color)
      index+=1
    return medoids

"""# **Return the value of medoid[i] closest between the color of pixel x,y and the list of medoids, uses the Euclidean distance to calculate the proximity**"""

#Euclidean Distance of rgb values
def EuclideanDistance(color1, color2):
  return math.sqrt(pow((color1[0]-color2[0]),2)+pow((color1[1]-color2[1]),2)+pow((color1[1]-color2[1]),2))

#use the Euclidean Distance for estimate the distance between 2 colors and get the minimum distance
def getClosest(color, medoids):
  closest=medoids[0]
  min_distance = EuclideanDistance(color,closest)
  for med in medoids:
    dist = EuclideanDistance(color,med)
    if dist < min_distance:
      min_distance = dist
      closest = med 
  return closest

"""# **Estrazione di BOCP e BOCC da un set mirato di GUI in un'app nativa Android.**"""

"""algorithm BOCP and BOCC. TheBOCP is a hash-map structure for all the pixels in the GUI, in which a key is a quantized color (color ∗) 
and the corresponding value (for a key) is a list of pixels assigned to that color.
The BOCC is a hash-map too, in which the key is a quantized color (color ∗) but the corresponding value is a set
of the components associated with the pixels in BOCP[color ∗]."""
def BOCP_BOCC_algorithm(k,r,GUIS):
  BOCP={}
  BOCC={}
  #iterate all guis
  for n_gui,GUI in enumerate(GUIS):
      print(GUI)
      S=PIL.Image.open(GUI+".png")
      #convert image in rgb
      S = S.convert("RGB")
      # Passing the path of the xml document to enable the parsing process
      tree = ET.parse(GUI+".uix")
      # getting the parent tag of the xml document
      root = tree.getroot()
      C=getComponentsFromSnapshot(root)
      # iterate all component in bottom up
      for c in reversed(C):
        pixel_c=pd.DataFrame()
        #check the length of the components and get respective pixels with relative rgb and component name
        if len(c)==17 and c[3][1].find("Image") == -1:
          pixel_c=getPixels(S,c,0)
        if len(c)==18 and c[4][1].find("Image") == -1:
          pixel_c=getPixels(S,c,1)   
        if not pixel_c.empty:  
          list_color=list(pixel_c["R-G-B"])
          histo_c=getPixelHistogramSorted(list_color)
          medoids=getMedoids(histo_c,k,r)
          i=0
          list_x=list(pixel_c["Axis-X"])
          list_y=list(pixel_c["Axis-Y"])
          for pixel_color in list_color:
            color_quant=getClosest(pixel_color,medoids)
            #first element is the  number of the interface 
            pixel_x_y = (n_gui,list_x[i],list_y[i])
            c_n=(n_gui,c)
            #hashmap of BOCP and BOCC, the keys are the quantized values
            BOCP.setdefault(color_quant,[]).append(pixel_x_y)
            BOCC.setdefault(color_quant,[]).append(c)
            i+=1
  return BOCP,BOCC

"""# **MAIN**"""

dir_list = os.listdir('Snapshot')
#k and r are assigned by the authors of the paper
k=3
r=1.6
#we get all the directories
for directory in dir_list:
  path="Snapshot/"+directory
  #we get all the guis 
  GUIS=getGUIS(path)
  #algorithm BCOP_BOC
  BOCP,BOCC=BOCP_BOCC_algorithm(k,r,GUIS)
  created_file="DatiSalvati/"+directory+"_BOCP.pickle"
  with open(created_file,"wb") as handle:
    pickle.dump(BOCP, handle,protocol=pickle.HIGHEST_PROTOCOL)
    created_file="DatiSalvati/"+directory+"_BOCC.pickle"
  with open(created_file,"wb") as handle:
    pickle.dump(BOCC, handle,protocol=pickle.HIGHEST_PROTOCOL)