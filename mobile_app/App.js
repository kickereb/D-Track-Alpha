// "use client";
import {Canvas, Path, Skia, vec, Points, Rect, Text, matchFont, center } from "@shopify/react-native-skia";
import React, {useState, useEffect, createContext, useContext } from "react";
import { StyleSheet, View, TouchableOpacity, Platform, Button, useWindowDimensions, Text as DefText } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createDrawerNavigator, DrawerContentScrollView, DrawerItemList, DrawerItem } from "@react-navigation/drawer";
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth, onLogout, AuthProvider, API_URL } from "./AuthContext";
import AuthNavigator from "./AuthNavigator";
import * as SecureStore from "expo-secure-store";
import axios from "axios";

var visible = [];

const togglePath = (target) => {
  const index = visible.findIndex(t => t.target === target)
  if (visible[index].v == 1) {
    visible[index].v = 0
  } else if (visible[index].v == 0) {
    visible[index].v = 1
  }
}




function MainScreen({ navigation }) {
  const {d, setData} = React.useContext(DataContext);
  const {v, setVisibility} = React.useContext(VisibilityContext);
  const { onLogout } = useAuth();

  var outPath = [];
  var outPoints = [];

  const paddingX = 20;
  const paddingY = 50;
  const offset = 30;

  const {width, height} = useWindowDimensions();
  

  var definedArea = {w:500, h:700};

  // const cDim = {w:350, h:400};

  const cDim = {w:width*95/100-paddingX-offset, h:height*70/100-paddingY-offset};
  
  const drawDim = {w: cDim.w-offset, h: cDim.h-offset}

  var scaleX = drawDim.w/definedArea.w;
  var scaleY = drawDim.h/definedArea.h;


  const allowedColors = ["#e60049", "#0bb4ff", "#50e991", "#e6d800", "#9b19f5", "#ffa300", "#dc0ab4", "#b3d4ff", "#00bfa0"];

  const sortData = (dataArr) => {
    var result = [];
    var seen = [];
    
    for (var i=0;i<dataArr.length;i++) {
      if (!seen.some(k => k === dataArr[i].target)) {
        var temp = [{x: dataArr[i].x, y: dataArr[i].y, target: dataArr[i].target, seq: dataArr[i].id}];
        seen.push(dataArr[i].target);
        result.push(temp);
        if (!visible.some(t => t.target === dataArr[i].target)) {
          visible.push({v:1, target: dataArr[i].target})
        }
      } else {
        result[seen.indexOf(dataArr[i].target)].push({x: dataArr[i].x, y: dataArr[i].y, target: dataArr[i].target, seq: dataArr[i].id});
      }
    }

    result.sort((a,b)=>(a.seq - b.seq)) 
  
    for (var i=0;i<visible.length;i++) {
      if (!seen.some(k => k === visible[i].target)) {
        visible.splice(i);
      } 
    }
    return result;
  }

  const scaleData = (dataArray) => {
    // console.log(dataArray)
    var temp = dataArray;
    for (var i=0;i<temp.length;i++) {
      for (var j=0;j<temp[i].length;j++) {
        temp[i][j].x = temp[i][j].x*scaleX
        temp[i][j].y = temp[i][j].y*scaleY;
        // Il include it here after testing
        // dArr[i][j].y = cDim.h - dArr[i][j].y
      }
    }
    return temp;
  }

  const drawPath = (dArr) => {
    const path = Skia.Path.Make();
    path.moveTo(parseFloat(dArr[0].x)+offset+paddingX,cDim.h-offset+paddingY-parseFloat(dArr[0].y))
    for (var i=1;i<dArr.length;i++) {
      path.lineTo(parseFloat(dArr[i].x)+offset+paddingX, cDim.h-offset+paddingY-parseFloat(dArr[i].y));
    }
    return path;
  }

  const drawPoints = (dArr) => {
    var points = [];
    for (var i=0;i<dArr.length;i++) {
      points.push(vec(parseFloat(dArr[i].x)+offset+paddingX,cDim.h-offset+paddingY-parseFloat(dArr[i].y)));
    }
    return points;
  }

  const renderAxis = () => {

    const p = Skia.Path.Make();
    // X Axis
    p.moveTo(offset+paddingX, cDim.h-offset+paddingY);
    p.lineTo(cDim.w+paddingX,cDim.h-offset+paddingY);
    
    // Y Axis
    p.moveTo(offset+paddingX, cDim.h-offset+paddingY);
    p.lineTo(offset+paddingX,0+paddingY);

    return (<Path key= {"axis"} path = {p} style="stroke" strokeWidth={2} color="black"></Path>)
  }

  const renderTicks = () => {
    var ticks = [];
    const p = Skia.Path.Make();
    const fsize = 12;
    const fontFamily = Platform.select({ ios: "Helvetica", android: "sans-serif", default: "sans-serif" });

    const fontStyle = {
      fontFamily,
      fontSize: fsize,
      fontStyle: "normal",
      fontWeight: "normal",
    };
    const font = matchFont(fontStyle);

    const xTicks = 5;
    const yTicks = 7;

    // const xTicks = parseInt(definedArea.w/100);
    // const yTicks = parseInt(definedArea.h/100);

    const xDimInc = (drawDim.w/xTicks);
    const xValueInc = definedArea.w/xTicks;
    var diff = 0;

    for (var i=0;i<=xTicks;i++) {
      diff = (Math.round(xValueInc*i*100)/100+"").length;
      
      // console.log((i*xDimInc)+offset+"")
      // console.log(diff);

      p.moveTo((i*xDimInc)+offset+paddingX, cDim.h-offset+paddingY);
      p.lineTo((i*xDimInc)+offset+paddingX, cDim.h-offset+8+paddingY);

      ticks.push(<Text key={"xtext"+i} x={(i*xDimInc)+offset+paddingX-(diff*3.3)} y={drawDim.h+20+paddingY} text={Math.round(xValueInc*i*100)/100+""} font = {font}/>)
    }

    const yDimInc = (drawDim.h/yTicks);
    const yValueInc = definedArea.h/yTicks;
    var counter = 0;
    for (var i=yTicks;i>=0;i--) {
      diff = (Math.round(yValueInc*counter*100)/100+"").length;

      p.moveTo(offset+paddingX, i*yDimInc+paddingY);
      p.lineTo(offset+paddingX-8, i*yDimInc+paddingY);

      ticks.push(<Text key={"ytext"+i} x={offset+paddingX-(diff*5.5)-14} y={(i*yDimInc+paddingY+4)} text={Math.round(yValueInc*counter*100)/100+""} font = {font}/>)
      counter = counter + 1
    }

    ticks.push(<Path key={"ticksp"+i} path = {p} style="stroke" strokeWidth={1} color="black"></Path>)
    
    return ticks;
  }

  const renderPath = (arr) => {
    var out = [];
    for (let i=0;i<arr.length;i++) {
      const p = drawPath(arr[i]);
      const ukey = "pathkey"+i;
      if (visible[i].v === 1) {
        out.push(
          <Path key={ukey} path={p} style="stroke" strokeWidth={4} color={allowedColors[i%allowedColors.length]}/>
        );
      }
      
    }
    return out;
  }

  const renderPoints = (arr) => {
    var out = [];
    for (let i=0;i<arr.length;i++) {
      const p = drawPoints(arr[i]);
      const ukey = "pointskey"+i;
      if (visible[i].v === 1) {
        out.push(
          <Points key={ukey} points={p} mode="points" color="#1f1e33" style="fill" strokeWidth={6}></Points>
        )
      }
      
    }
    return out;
  }


  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`${API_URL}/`)
          setData(response.data);
      } catch (error) {
        console.log(error.response.data.err, error);
        onLogout();
      }
    }
    fetchData();
  }, []);

  const test = scaleData(sortData(d));

  outPath = renderPath(test);
  outPoints = renderPoints(test);
  
  const axis = renderAxis();
  const ticks = renderTicks();
  
  useEffect(()=> {
    setVisibility(visible)
  },[])
  
  // console.log(v)
  return (
    <>
      <View style={styles.container}>
          <Canvas style={{width: cDim.w+offset+paddingX, height: cDim.h+offset+paddingY, alignSelf:"center"}}>
            <Rect x={offset+paddingX} y={paddingY} width={drawDim.w} height={drawDim.h} color="#E1E1E1"></Rect>
            
            {axis}
            {ticks}
            {outPath}
            {outPoints}
            {/* <Path path={p} style="stroke" strokeWidth={4} color="#3EB489"/>
            <Points points={pts} mode="points" color="red" style="fill" strokeWidth={6}></Points> */}
          </Canvas>
          <TouchableOpacity style={styles.refreshButton} onPress={async ()=> {
              await axios.get(`${API_URL}/`).then(response => response.data)
              .then(data => setData(data))
              .catch(error => {console.error(error);onLogout()});
              
              setVisibility(visible)
              } } 
            title="Refresh Data">

              <DefText style={styles.refreshText}>Refresh Data</DefText>

            </TouchableOpacity>
          {/* <Button onPress={}></Button> */}
      </View>
    </>
  )
}




function ListItems(props) {
  const {v, setVisibility} = React.useContext(VisibilityContext);
  const {d, setData} = React.useContext(DataContext)

  const renderDrawPathItems = (vis) => {
    var out = [];
    for (var i=0; i<vis.length; i++) {
      const tar = vis[i].target+"";
      out.push(<DrawerItem key={tar} label={tar} onPress={async ()=>{togglePath(tar); 
        await axios.get(`${API_URL}/`).then(response => response.data)
              .then(data => setData(data))
              .catch(error => {console.error(error); onLogout()});
      }}></DrawerItem>)
    }
    return out;
  }

  const drawItems = renderDrawPathItems(v);

  return (
    <DrawerContentScrollView {...props}>
      <DrawerItemList {...props} />
      {/* <DrawerItem label="Test" onPress={()=>{togglePath("hi"); }}
      /> */}
      {drawItems}
    </DrawerContentScrollView>
    
  )
}


function PathList() {
  return (
    <Drawer.Navigator
      drawerContent={(props) => <ListItems {...props} />}
    >
      <Drawer.Screen name="Paths" component={MainScreen} options ={{ drawerItemStyle: { display: 'none'}}} />
    </Drawer.Navigator>
  )
}

function AuthNavi() {
  const { authState, onLogout } = useAuth();

  return (
    <NavigationContainer>
        {
          authState.authorised ? 
          <Auth.Navigator>
            <Auth.Screen name="Home" component={PathList} options={{
              headerRight: () => <TouchableOpacity style={styles.logoutButton} onPress={onLogout} title = "Log out">
                <DefText Style={styles.logoutText}>Log out</DefText>
              </TouchableOpacity>
            }} />
          </Auth.Navigator>:
          <AuthNavigator />
        }
        
    </NavigationContainer>
  )
}


const Drawer = createDrawerNavigator();
const Auth = createNativeStackNavigator();

const DataContext = React.createContext([]);
const VisibilityContext = React.createContext([]);


export default function App() {
  const [d, setData] = React.useState([]);
  const [v, setVisibility] = React.useState([]);
  
  // var arr = sortData(d);
  // console.log(arr)
  
  return (
    <AuthProvider>
      <DataContext.Provider value={{ d, setData }}>
        <VisibilityContext.Provider value={{v, setVisibility}}>
          <AuthNavi/>
        </VisibilityContext.Provider>
      </DataContext.Provider>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 100,
    width: "100%",
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  refreshButton: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
    width: "40%",
    paddingHorizontal: 32,
    borderRadius: 3,
    elevation: 3,
    backgroundColor: '#e0e0e0',
  },
  refreshText: {
    fontSize: 16,
    color:"#1f1e33"
  },
  logoutText: {
    fontSize: 18,
    color:"#1f1e33"
  }
});