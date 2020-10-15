#!/usr/bin/env python

####################################################
##                                                ## 
## This script creates masks of near land points  ##
##                                                ##
####################################################

# import modules
from glob import glob
import os,sys
import numpy as np
import netCDF4 as nc
import matplotlib.pyplot as plt

# paths
src_data_dir = '/g/data/ik11/inputs/WOA13v2/averaged_decades/'
# output paths
dst_data_dir = '/g/data/ik11/inputs/access-om2/woa13/monthly/'

print('Importing WOA13 raw data')
mon = ['01','02','03','04','05','06','07','08','09','10','11','12']
deepmon = ['13','13','13','14','14','14','15','15','15','16','16','16']
i = 0
for mm in range(0,len(mon)):
    i = i+1
    # get upper ocean temp data:
    woa_file = src_data_dir+'woa13_decav_t'+mon[mm]+'_04v2.nc'
    print(woa_file)
    ncFile = nc.Dataset(woa_file)
    lat = ncFile.variables['lat'][...]
    #lat_bnds = ncFile.variables['lat_bnds'][...]
    #lon_bnds = ncFile.variables['lon_bnds'][...]
    #depth_upper_bnds = ncFile.variables['depth_bnds'][...]
    depth_upper = ncFile.variables['depth'][...]
    lon = ncFile.variables['lon'][...]
    t_in_situ_upper = ncFile.variables['t_an'][0,...]
    #time = ncFile.variables['time'][...]

    # get upper ocean salinity data:
    #woa_file = data_dir+'woa13_decav_s01_04v2.nc'
    woa_file = src_data_dir+'woa13_decav_s'+mon[mm]+'_04v2.nc'
    print(woa_file)
    ncFile = nc.Dataset(woa_file)
    s_practical_upper = ncFile.variables['s_an'][0,...]

    # get lower ocean temp data:
    #woa_file = data_dir+'woa13_decav_t13_04v2.nc'
    woa_file = src_data_dir+'woa13_decav_t'+deepmon[mm]+'_04v2.nc'
    print(woa_file)
    ncFile = nc.Dataset(woa_file)
    depth_lower = ncFile.variables['depth'][...]
    t_in_situ_lower = ncFile.variables['t_an'][0,...]
    
    # get lower ocean salinity data:
    #woa_file = data_dir+'woa13_decav_s13_04v2.nc'
    woa_file = src_data_dir+'woa13_decav_s'+deepmon[mm]+'_04v2.nc'
    print(woa_file)
    ncFile = nc.Dataset(woa_file)
    s_practical_lower = ncFile.variables['s_an'][0,...]
    
    # combine January for upper ocean with winter below 1500m:
    t_in_situ = np.copy(t_in_situ_lower)
    t_in_situ[:len(depth_upper),:,:] = t_in_situ_upper
    s_practical = np.copy(s_practical_lower)
    s_practical[:len(depth_upper),:,:] = s_practical_upper
    depth = depth_lower
    del t_in_situ_lower,t_in_situ_upper,s_practical_lower,s_practical_upper
   
    # mask t_in_situ and s_practical before doing calculations:
    t_in_situ = np.ma.masked_where(t_in_situ>1000,t_in_situ)
    s_practical = np.ma.masked_where(s_practical>1000,s_practical)
    
    # convert in situ temperature to conservative temperature:
    import gsw
    print('Calculating pressure from depth')
    longitude,latitude=np.meshgrid(lon,lat)
    depth_tile = (np.tile(depth,(len(lat),1))).swapaxes(0,1)
    pressure = gsw.p_from_z(-depth_tile,lat)
    pressure_tile = np.tile(pressure,(1440,1,1)).swapaxes(0,2).swapaxes(0,1)
    del pressure
    
    # having memory issues, so do level by level:
    s_absolute = np.zeros_like(s_practical)
    for kk in range(0,len(depth)):
    	if kk%10 == 0:
    		print('Calculating absolute salinity for level '+str(kk))
    	s_absolute[kk,:,:] = gsw.SA_from_SP(s_practical[kk,:,:],pressure_tile[kk,:,:],
    		longitude,latitude)
    del longitude,latitude
    
    print('Calculating conservative temperature from in situ temperature')
    t_conservative = gsw.CT_from_t(s_absolute,t_in_situ,pressure_tile)
    
    # save to netcdf
    #save_file = data_dir + 'woa13_decav_ts_jan_04v2.nc'
    save_file = dst_data_dir + 'woa13_decav_ts_'+mon[mm]+'_04v2.nc'
    print(save_file)
    ncFile = nc.Dataset(save_file,'r+')
    
    # overwrite time
    ncFile.variables['time'][0] = i
    ncFile.variables['time'].units = 'months since 0001-01-01 00:00:00'
    # overwrite salinity with data including January near surface values:
    ncFile.variables['practical_salinity'][0,...] = s_practical
    
    # add variable for conservative temperature:
    t_var = ncFile.createVariable('conservative_temperature', 'f4', ('time','depth',\
                   'lat','lon'),fill_value=9.96921e+36)
    t_var.units = 'degrees celsius'
    t_var.long_name = 'conservative temperature calculated using teos10 from objectively'+\
    	' analysed mean fields for sea_water_temperature'
    t_var[0,:] = t_conservative

#s_var = ncFile.createVariable('practical_salinity', 'f4', ('time','depth','lat','lon'),fill_value=9.96921e+36)
#s_var.units = '1'
#s_var.grid_mapping = "crs"
#s_var.long_name = 'Objectively analyzed mean fields for sea_water_salinity at standard depth levels.'
#s_var.missing_value =  9.96921e+36
#s_practical[np.where(np.isnan(s_practical)==True)] = 9.96921e+36
#s_var[0,:] = s_practical

ncFile.close()

