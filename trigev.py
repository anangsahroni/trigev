import pandas as pd
import obspyDMT.utils.event_handler as event
from obspy.geodetics import locations2degrees
from obspy.taup import TauPyModel
import matplotlib
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.io.shapereader import Reader
from cartopy.feature import ShapelyFeature
import cartopy.io.img_tiles as cimgt
from cartopy.io.shapereader import Reader
from cartopy.feature import ShapelyFeature
import cartopy.feature as cfeature

font = {'size'   : 8}
matplotlib.rc('font', **font)
        
pd.options.mode.chained_assignment = None

class TRIGEV:
    triggering_catalog=[]
    triggered_catalog=[]
    each_triggered_temp_catalog=[]
    each_triggering_temp_catalog=[]
    selected_index=0
    time_window=[]
    
    
    def __init__(self, min_mag, event_rect, min_date, max_date, server):
        self.min_mag = min_mag
        self.event_rect = event_rect
        self.min_date = min_date
        self.max_date = max_date
        self.server = server
        
    def download(self, triggered_local=None, triggering_local=None):
        triggered_catalog_dict = dict(datapath="./temp_triggered",
            evlatmin=self.event_rect[0],
            evlatmax=self.event_rect[2],
            evlonmin=self.event_rect[1],
            evlonmax=self.event_rect[3],
            min_depth=10,
            max_depth=500,
            max_mag=10,
            mag_type="Mw",
            evlat=None,
            evlon=None,
            evradmin=None,
            evradmax=None,
            read_catalog=None,
            min_mag=3,
            min_date=self.min_date,
            max_date=self.max_date,
            event_catalog=self.server,
            preset=0,
            offset=1800,)
        
        triggering_catalog_dict = dict(datapath="./temp_triggering",
            evlatmin=-90,
            evlatmax=90,
            evlonmin=-180,
            evlonmax=180,
            min_depth=10,
            max_depth=500,
            max_mag=10,
            mag_type="Mw",
            evlat=None,
            evlon=None,
            evradmin=None,
            evradmax=None,
            read_catalog=None,
            min_mag=self.min_mag,
            min_date=self.min_date,
            max_date=self.max_date,
            event_catalog=self.server,
            preset=0,
            offset=1800,)
        
        if triggering_local != None:
            triggering_catalog = pd.read_csv(triggering_local)
        else:
            data_triggering = event.event_info(input_dics=triggering_catalog_dict)
            print(data_triggering)
            triggering_catalog = pd.DataFrame(data_triggering[0], columns=data_triggering[0][0].keys())
            
        if triggered_local != None:
            triggered_catalog = pd.read_csv(triggered_local)
        else:
            data_triggered = event.event_info(input_dics=triggered_catalog_dict)
            print(data_triggered)
            triggered_catalog = pd.DataFrame(data_triggered[0], columns=data_triggered[0][0].keys())
        
        #triggering_catalog['datetime'] =  pd.to_datetime(triggering_catalog['datetime'], format='%Y-%m-%dT%H:%M:%S.%fZ')
        triggering_catalog.sort_values(by="datetime", inplace=True, ascending=False)
        triggering_catalog.reset_index(inplace=True)
        self.triggering_catalog = triggering_catalog
        
        #triggered_catalog['datetime'] =  pd.to_datetime(triggered_catalog['datetime'], format='%Y-%m-%dT%H:%M:%S.%fZ')
        triggered_catalog.sort_values(by="datetime", inplace=True, ascending=False)
        triggered_catalog.reset_index(inplace=True)
        self.triggered_catalog = triggered_catalog
        
        
    def find(self, event_index=0, oneday_time=2, s_end_threshold=3600, velocity_model="iasp91"):
        index=event_index
        triggering=self.triggering_catalog[self.triggering_catalog.event_id == self.triggering_catalog.event_id[index]]
        self.each_triggering_temp_catalog=triggering
        oneday_triggered=self.triggered_catalog[(self.triggered_catalog.datetime >=triggering.datetime.iloc[0])\
                                       &(self.triggered_catalog.datetime < (triggering.datetime.iloc[0] +pd.Timedelta(days=oneday_time)))]
        oneday_triggered.reset_index(inplace=True)

        s_surface_tolerance=s_end_threshold
        model = TauPyModel(model=velocity_model)
        distances, s_arrivals, triggered_status =[],[],[]
        for i,m in enumerate(oneday_triggered.magnitude):
            distance=locations2degrees(triggering.latitude.iloc[0], triggering.longitude.iloc[0], \
                                       oneday_triggered.latitude[i], oneday_triggered.longitude[i])
            s_arrivals_dict = model.get_travel_times(source_depth_in_km=triggering.depth.iloc[0],
                                              distance_in_degree=distance, phase_list=["S","Sdiff","SKIKS"])

            
            if len(s_arrivals_dict) != 0:
                s_arrivals_time = s_arrivals_dict[0].time
                if oneday_triggered.datetime[i] > (triggering.datetime.iloc[0]+pd.Timedelta(days=(s_arrivals_time/3600/24))) and \
                oneday_triggered.datetime[i] <= (triggering.datetime.iloc[0]+pd.Timedelta(days=((s_arrivals_time+s_surface_tolerance)/3600/24))):
                    triggered_status.append(True)
                    s_arrivals.append(triggering.datetime.iloc[0]+pd.Timedelta(days=(s_arrivals_time/3600/24)))
                else:
                    s_arrivals.append(triggering.datetime.iloc[0])
                    triggered_status.append(False)
            else:
                triggered_status.append(False)
                s_arrivals.append(triggering.datetime.iloc[0])
                
            distances.append(distance)
           

        oneday_triggered['distance']=distances
        oneday_triggered['s_arrivals']=s_arrivals
        oneday_triggered['trig_status']=triggered_status
        self.each_triggered_temp_catalog = oneday_triggered
        self.selected_index=event_index
        self.time_window=oneday_time
    
    def plot(self, output_file=None, fault_shapefile=None, tile_zoom=9):


        fig1 = plt.figure(facecolor="white")
        ax1 = fig1.add_subplot(projection=ccrs.PlateCarree())

        gl = ax1.gridlines(draw_labels=True, dms=False, x_inline=False, y_inline=False, \
                           zorder=11, alpha=.5, linewidth=.5)
        gl.top_labels = False
        gl.right_labels = False

        stamen_terrain = cimgt.Stamen('terrain-background') ##maps.stamen.com
        ax1.add_image(stamen_terrain,tile_zoom)
        
        # disabled because server is down
        # land
        #ax1.add_feature(cfeature.LAND, color="lightgrey")
        # add coastline
        #ax1.add_feature(cfeature.COASTLINE, linewidth=.5, zorder=11)

        if fault_shapefile:
          fault_reader = Reader(fault_shapefile)
          fault_feature = ShapelyFeature(fault_reader.geometries(),
                                                  ccrs.Mercator(), edgecolor='black')
          ax1.add_feature(fault_feature, linewidth=.4, facecolor="none", edgecolor="black", zorder=12)
        
        oneday_triggered=self.each_triggered_temp_catalog
        triggering=self.triggering_catalog[self.triggering_catalog.index == self.selected_index]
        possibly_triggered=oneday_triggered[oneday_triggered.trig_status == True]
        oneday_event = oneday_triggered[oneday_triggered.trig_status == False]
        ax1.scatter(oneday_event.longitude, oneday_event.latitude, label="{}-d window after EQ".format(self.time_window),zorder=110, edgecolor="green")
        ax1.scatter(possibly_triggered.longitude, possibly_triggered.latitude, label="Possibly Triggered EQ",zorder=110, edgecolor="red")
        ax1.plot(triggering.longitude.iloc[0],triggering.latitude.iloc[0],marker="*", label="Triggering EQ", color="yellow",\
                    markeredgecolor="black",markersize=16,transform=ccrs.PlateCarree(), zorder=110)
        legend=ax1.legend()
        legend.set_zorder(110)
        if output_file:
          fig1.savefig(output_file, dpi=300)
