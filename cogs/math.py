"""
Last Updated:

"""

import discord
from discord.ext import commands
from typing import Union
import math
import time

class Conversion(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.__class__.__name__} ready!')

    """

    Conversion Factors
    - base unit is equivalent to 1
    - dimensional analysis

    """

    lengthConvert = {
        'hm':1,
        'km':0.1,
        'dam':10,
        'm':100,
        'dm':1000,
        'cm':10000,
        'mm':100000,
        'mum':100000000,
        'nm':100000000000,
        'in':100000*(1/25.4),
        'league':100000*(1/25.4)/190080,
        'mi':100000*(3/25.4)/190080,
        'ft':100000*(15840/25.4)/190080,
        'yd':100000*(5280/25.4)/190080
        }

    areaConvert = {
        'km2':1,
        'ha':100,
        'm2':1000000,
        'cm2':10000000000,
        'mm2':1000000000000,
        'mum2':1000000000000000000,
        'mi2':0.3861018768,
        'yd2':1195990.0463,
        'ft2':10763910.417,
        'in2':1550003100,
        'acre':247.10538147
        }

    volumeConvert = {
        'm3':1,
        'mL':1/0.000001,
        'barrel':1/0.158987294928,
        'ft3':1/0.028316846592,
        'dm3':1/0.001,
        'L':1/0.001,
        'gal':1/0.003785411784,
        'pint':1/0.000473176473,
        'in3':1/0.000016387064,
        'cm3':1/0.000001,
        'oz':33814
        }

    pressureConvert = {
        'Pa':1,
        'atm':1/101325,
        'bar':0.00001,
        'lb/in2':1/6895,
        'Torr':1/133,
        'mmHg':1/133
        }

    timeConvert = {
        'yr':1,
        'mon':12,
        'd':365,
        'w':365/7,
        'h':365*24,
        'min':365*24*60,
        's':365*24*60*60,
        'ms':365*24*60*60*1000,
        'mus':365*24*60*60*1000000,
        'ns':365*24*60*60*1000000000
        }

    weightConvert = {
        'ton':1,
        'kg':1000,
        'g':1000000,
        'mg':1000000000,
        'lb':2204.6244202,
        'oz':35273.990723,
        'carat':5000000,
        'amu':6.022136652e29
        }

    speedConvert = {
        'm/s':1,
        'ft/s':3.2808453346457,
        'mph':2.2369400008947954994,
        'kph':3.6000059687997456592,
        'knot':1.9438477170141412742
        }

    energyConvert = {
        'cal':1,
        'J':4.184,
        'kJ':0.004184,
        'KJ':0.004184,
        'kcal':1/1000,
        'wh':1/860.421,
        'kwh':1/860421,
        'ev':2.611e+19,
        'btu':1/252,
        'therm':1/2.521e7,
        'ft-lb':3.08596
        }

    angleConvert = {
        'deg':1,
        'rad':math.pi/180,
        'grad':200/180,
        'mrad':1000*math.pi/180,
        'arcmin':60,
        'arcsec':3600
        }

    """

    Unit Abbreviations

    """

    measureUnits = {
        'hm':'hectometers',
        'dam':'dekameters',
        'km':'kilometers',
        'm':'meters',
        'dm':'decimeters',
        'cm':'centimeters',
        'mm':'millimeters',
        'mum':'micrometers',
        'nm':'nanometers',
        'in':'inches',
        'league':'leagues',
        'mi':'miles',
        'ft':'feet',
        'yd':'yards',
        'm3':'cubic meters',
        'mL':'milliliters',
        'barrel':'barrels',
        'ft3':'cubic feet',
        'L':'liters',
        'gal':'gallons',
        'pint':'pints',
        'in3':'cubic inches',
        'cm3':'cubic centimeters',
        'Pa':'pascals',
        'atm':'standard atmosphere',
        'bar':'bars',
        'lb/in2':'pounds per square inch',
        'Torr':'Torrs',
        'mmHg':'millimeters of mercury',
        'C':'degrees Celsius',
        'F':'degrees Fahrenheit',
        'K':'Kelvin',
        'R':'Rankine',
        'Re':'Reaumur',
        'Ro':'Romer',
        'yr':'years',
        'mon':'months',
        'd':'days',
        'w':'weeks',
        'h':'hours',
        'min':'minutes',
        's':'seconds',
        'ms':'milliseconds',
        'mus':'microseconds',
        'ns':'nanoseconds',
        'ton':'metric tons',
        'kg':'kilograms',
        'g':'grams',
        'mg':'milligrams',
        'lb':'pounds',
        'oz':'ounces',
        'carat':'carats',
        'amu':'atomic mass units',
        'km2':'square kilometers',
        'm2':'square meters',
        'cm2':'square centimeters',
        'mm2':'square millimeters',
        'mum2':'square micrometers',
        'ha':'hectares',
        'mi2':'square miles',
        'yd2':'square yards',
        'ft2':'square feet',
        'in2':'square inches',
        'acre':'acres',
        'm/s':'meters per second',
        'ft/s':'feet per second',
        'mph':'miles per hour',
        'kph':'kilometers per hour',
        'knot':'knots',
        'cal':'calories',
        'J':'joules',
        'kJ':'kilojoules',
        'KJ':'kilojoules',
        'kcal':'kilocalories',
        'wh':'watt-hour',
        'kwh':'kilowatt-hour',
        'ev':'electron-volts',
        'btu':'british thermal units',
        'therm':'therms',
        'ft-lb':'foot-pounds',
        'deg':'degrees',
        'rad':'radians',
        'grad':'gradians',
        'mrad':'milliradians',
        'arcmin':'minutes of an arc',
        'arcsec':'seconds of an arc'
        }

    def toCelsius(self,unit):
        if unit == 'F':
            return 5/9*self.x-(160/9)
        elif unit == 'K':
            return self.x-273.15
        elif unit == 'R':
            return 5/9*self.x-273.15
        elif unit == 'Re':
            return 5/4*self.x
        elif unit == 'Ro':
            return 40/21*(self.x-7.5)
        else:
            return self.x

    def convertTemp(self,unit):
        if unit == 'F':
            return 9/5*self.c+32
        elif unit == 'K':
            return self.c+273.15
        elif unit == 'R':
            return 9/5*(self.convertTemp('K'))
        elif unit == 'Re':
            return 4/5*self.c
        elif unit == 'Ro':
            return 21/40*self.c+7.5
        else: #toCelsius
            return self.c

    @commands.command()
    async def convert(self,ctx, givenUnits=None,measurement: Union[int,float]=None):
        start_time = time.time()
        ### CONVERT MEASUREMENT UNITS ###

        tempUnits = ['C','F','K','R','Re','Ro']

        convertUnits = [
            self.lengthConvert,
            self.volumeConvert,
            self.timeConvert,
            self.pressureConvert,
            self.weightConvert,
            self.speedConvert,
            self.energyConvert,
            self.angleConvert,
            self.areaConvert
            ]


        if givenUnits is None:
            return await ctx.send(f'❌ | Wrong Syntax\n\n`Syntax: {ctx.prefix}convert `unitA`>`unitB` measurement`',delete_after=2)

        units = givenUnits.split('>')
        unit1 = units[0] # ORIGINAL UNIT
        unit2 = units[1] # CONVERTED UNIT

        if(unit1 == unit2):
            # SAME UNITS
            return await ctx.send('❌ | Cannot convert same units!',delete_after=2.0)
        elif(unit1 not in self.measureUnits.keys() or unit2 not in self.measureUnits.keys()):
            # INVALID UNITS
            return await ctx.send('❌ | Please enter valid units.',delete_after=2.0)
        else:
            result ,footer = None, None
            self.x = measurement
            if unit1 in tempUnits and unit2 in tempUnits:
                self.c = self.toCelsius(unit1)
                result = self.convertTemp(unit2)
            else:
                for unit in convertUnits:
                    if unit1 in unit.keys() and unit2 in unit.keys():
                        result = measurement*(unit[unit2]/unit[unit1])
                        footer = f'{unit[unit1]/unit[unit1]} {unit1} = {unit[unit2]/unit[unit1]} {unit2}'
                        break
            if result is None:
                return await ctx.send('❌ | Please enter complementary units.',delete_after=3.0)
            if result >= 99999 or result < 0.001:
                result = '{:.3e}'.format(result)
            elif isinstance(result,float):
                result = '{:.5f}'.format(result).rstrip('0')
            embed = discord.Embed(color=discord.Colour.green(),
                                  title='{} {}'.format(str(result).replace('e',' × 10^').replace('+',''),self.measureUnits[unit2]),
                                  description=f'Converted from {measurement} {self.measureUnits[unit1]}')
            if footer:
                embed.set_footer(text=footer)
            await ctx.send(embed=embed)
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')

    @commands.command()
    async def units(self,ctx,category=None):
        start_time = time.time()
        if category is not None:
            if category.lower() not in ['angle','area','energy','length','pressure','speed','temp','temperature','time','volume','weight']:
                return await ctx.send('❌ | Category not found.',delete_after=3)
            if category == 'temp':
                category = 'temperature'
            units = open(f'cogs/extras/{category}.txt').readlines()
            #print(units)
            embed,values = discord.Embed(title='Conversion Units'),[]
            for unit in units:
                values.append((f"`{unit.split(':')[1][:-1]}` :: {unit.split(':')[0]}"))
            #print(values)
            embed.add_field(name=category.capitalize(),value='\n'.join(values))
            await ctx.send(embed=embed)
            return print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
        else:
            pages=[]
            for category in ['length','area','volume','weight','temperature','pressure','speed','time','energy','angle']:
                units = open(f'cogs/extras/{category}.txt').readlines()
                #print(units)
                embed,values = discord.Embed(title='Conversion Units'),[]
                for unit in units:
                    values.append((f"`{unit.split(':')[1][:-1]}` :: {unit.split(':')[0]}"))
                embed.add_field(name=category.capitalize(),value='\n'.join(values))
                pages.append(embed)
            for n in range(1,len(pages)+1):
                pages[n-1].set_author(name=f'Page {n}/{len(pages)}')
            message = await ctx.send(embed=pages[0])
            for reaction in ['⏪','◀️','▶️','⏩']:
                await message.add_reaction(reaction)
            print(f'{self.__class__.__name__} - {ctx.command} | {time.time()-start_time} s')
            i = 0
            while(1):
                reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: str(reaction.emoji) in ['⏪','◀️','▶️','⏩'] and reaction.message==message and user != self.bot.user)
                if str(reaction[0].emoji) == '⏪':
                    await message.edit(embed=pages[0])
                elif str(reaction[0].emoji) == '◀️':
                    if i>0:
                        i-=1
                        await message.edit(embed=pages[i])
                elif str(reaction[0].emoji) == '▶️':
                    if i<len(pages)-1:
                        i+=1
                        await message.edit(embed=pages[i])
                else:
                    i=len(pages)-1
                    await message.edit(embed=pages[i])
                await message.remove_reaction(reaction[0].emoji,reaction[1])

    @commands.command()
    async def gwa(self,ctx,user_level:int=None):
        ### COMPUTE FOR GWA GIVEN GRADES ###

        ############################
        ### SUBJECTS AND WEIGHTS ###
        ############################
        grade_7 = {'IS':1.7,'Math':1.7,'English':1.3,'Computer Science':1.0,'Filipino':1.0,'SocSci':1.0,'PEHM':1.0,'ValEd':0.7,'AdTech/Art':1.0}
        grade_8 = {'IS':2.0,'Math':1.7,'English':1.3,'Computer Science':1.0,'Filipino':1.0,'SocSci':1.0,'PEHM':1.0,'ValEd':0.7,'AdTech/Art':1.0,'EarthSci':0.7}
        grade_9 = {'Bio':1.0,'Physics':1.0,'Chem':1.0,'Math':1.0,'English':1.0,'Computer Science':1.0,'Filipino':1.0,'SocSci':1.0,'PEHM':1.0,'Statistics':1.0}
        grade_10 = {'Bio':1.0,'Physics':1.0,'Chem':1.0,'Math':1.3,'English':1.0,'Computer Science':1.0,'Filipino':1.0,'SocSci':1.0,'PEHM':1.0,'Research':1.0}
        grade_10_elective = {'Bio':1.0,'Physics':1.0,'Chem':1.0,'Math':1.3,'English':1.0,'Computer Science':1.0,'Filipino':1.0,'SocSci':1.0,'PEHM':1.0,'Research':1.0,'Elective':1.0}
        syp = {'Core Science':1.7,'STEM Elective':1.7,'Research':2.0,'Math':1.0,'English':1.0,'Filipino':1.0,'SocSci':1.0}
        ############################
        ### SUBJECTS AND WEIGHTS ###
        ############################

        numeric_grades = [1.0,1.25,1.5,1.75,2.0,2.25,2.5,2.75,3.0,4.0,5.0]
        emojis = {'7️⃣':grade_7,'8️⃣':grade_8,'9️⃣':grade_9,'🔟':grade_10,'🔣':grade_10_elective,'🔠':syp}
        subjects,grades,weights = [],[],[]
        # GET GRADE LEVEL
        if user_level is None:
            embed = discord.Embed(color=0x2451f2, title='GWA Calculator',description='React with your corresponding grade level')
            embed.add_field(name='Legend',value='7️⃣ Grade 7\n8️⃣ Grade 8\n9️⃣ Grade 9\n🔟 Grade 10 (no elective)\n🔣 Grade 10 (w/ elective)\n🔠 SYP (Grade 11 & 12)')
            message = await ctx.send(embed=embed)
            for emoji in emojis.keys():
                await message.add_reaction(emoji)
            reaction = await self.bot.wait_for('reaction_add',check=lambda reaction,user: user == ctx.author and str(reaction.emoji) in emojis.keys())
            grade_level = emojis[str(reaction[0])]
        else:
            if user_level not in range(7,13):
                return await ctx.send('❌ | Invalid grade level.',delete_after=2.0)
            level_equiv = {7:grade_7,8:grade_8,9:grade_9,10:grade_10,11:syp,12:syp}
            grade_level = level_equiv[user_level]

        # GET GRADE FOR EACH SUBJECT IN GRADE LEVEL
        for subject,units in grade_level.items():
            message = await ctx.send(f'Please enter your grade for `{subject}`')
            while 1:
                try:
                    grade = await self.bot.wait_for('message',check=lambda message: message.author == ctx.author and message.channel == ctx.channel and (message.content.lower()=='stop' or float(message.content) in numeric_grades))
                except ValueError as e:
                    # ONLY INTEGER AND FLOAT INPUTS ARE ALLOWED
                    await ctx.send('❌ | Numeric inputs only.',delete_after=2.0)
                else:
                    if grade.content.lower()=='stop':
                        await message.delete()
                        return await ctx.send('*Process terminated.*',delete_after=2.0)
                    await grade.add_reaction('✅')
                    break
            grades.append(f"`{format(float(grade.content),'.2f')}` {subject}") # APPEND GRADE - SUBJECT COMBINATIONS
            weights.append(float(grade.content)*units) # GRADE X WEIGHT
            await grade.delete()
            await message.delete()
        if sum(weights)/sum(grade_level.values()) <= 1.5:
            # DIRECTOR'S LISTER WOW
            gwa = f'{str(sum(weights)/sum(grade_level.values()))[:5]} :regional_indicator_d::regional_indicator_l:'
        else:
            gwa = f'{str(sum(weights)/sum(grade_level.values()))[:5]}'

        # CREATE REPORT CARD EMBED
        report_card = discord.Embed(color=0x2451f2,title=f'{gwa}') # TITLE = GWA
        report_card.add_field(inline=True,name='Grades',value='\n'.join(grades)) # GRADE - SUBJECT
        report_card.set_author(name=ctx.author.display_name,icon_url=ctx.author.avatar.url)
        await ctx.send(embed=report_card)

    @commands.command()
    async def grade(self,ctx,raw_grade:Union[int,float]):
        if raw_grade >= 96:
            embed = discord.Embed(color=discord.Colour.green(), title='1.00',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='1.00 ranges from 96-100')
        elif raw_grade < 96 and raw_grade >= 90:
            embed = discord.Embed(color=discord.Colour.green(), title='1.25',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='1.25 ranges from 90-95.999')
        elif raw_grade < 90 and raw_grade >= 84:
            embed = discord.Embed(color=discord.Colour.green(), title='1.50',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='1.50 ranges from 84-89.999')
        elif raw_grade < 84 and raw_grade >= 78:
            embed = discord.Embed(color=discord.Colour.green(), title='1.75',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='1.75 ranges from 78-83.999')
        elif raw_grade < 78 and raw_grade >= 72:
            embed = discord.Embed(color=discord.Colour.green(), title='2.00',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='2.00 ranges from 72-77.999')
        elif raw_grade < 72 and raw_grade >= 66:
            embed = discord.Embed(color=discord.Colour.green(), title='2.25',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='2.25 ranges from 66-71.999')
        elif raw_grade < 66 and raw_grade >= 60:
            embed = discord.Embed(color=discord.Colour.green(), title='2.50',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='2.50 ranges from 65-71.999')
        elif raw_grade < 60 and raw_grade >= 55:
            embed = discord.Embed(color=discord.Colour.green(), title='2.75',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='2.75 ranges from 55-59.999')
        elif raw_grade < 55 and raw_grade >= 50:
            embed = discord.Embed(color=discord.Colour.green(), title='3.00',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='3.00 ranges from 50-54.999')
        elif raw_grade < 50 and raw_grade >= 40:
            embed = discord.Embed(color=discord.Colour.green(), title='4.00',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='4.00 ranges from 40-49.999')
        else:
            embed = discord.Embed(color=discord.Colour.green(), title='5.00',description=f'Transmuted from {raw_grade}')
            embed.set_footer(text='5.00 ranges from 0-39.999')
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Conversion(bot))
