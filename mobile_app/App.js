// "use client";
import {Canvas, Path, Skia, vec, Points, Rect, Text, matchFont } from "@shopify/react-native-skia";
import React, {useState, useEffect, createContext, useContext } from "react";
import { StyleSheet, View, Dimensions, Platform, Button } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createDrawerNavigator, DrawerContentScrollView, DrawerItemList, DrawerItem } from "@react-navigation/drawer";
import store from './store'
import { Provider } from 'react-redux'
import { Data } from "victory-native";

const sortData = (dataArr) => {
  var result = [];
  var seen = [];
  
  for (var i=0;i<dataArr.length;i++) {
    if (!seen.some(k => k === dataArr[i].target)) {
      var temp = [{x: dataArr[i].x, y: dataArr[i].y, target: dataArr[i].target}];
      seen.push(dataArr[i].target);
      result.push(temp);
      if (!visible.some(t => t.target === dataArr[i].target)) {
        visible.push({v:1, target: dataArr[i].target})
      }
    } else {
      result[seen.indexOf(dataArr[i].target)].push({x: dataArr[i].x, y: dataArr[i].y, target: dataArr[i].target});
    }
  }

  for (var i=0;i<visible.length;i++) {
    if (!seen.some(k => k === visible[i].target)) {
      visible.splice(i);
    } 
  }
  return result;
}

var visible = [];

const togglePath = (target) => {
  const index = visible.findIndex(t => t.target === target)
  if (visible[index].v == 1) {
    visible[index].v = 0
  } else if (visible[index].v == 0) {
    visible[index].v = 1
  }
  
  
}

const allowedColors = ["blue", "green", "yellow", "black", "white", "purple", "cyan", "magenta", "lime", "orange"];




const paddingX = 10;
const paddingY = 50;
var outPath = [];
var outPoints = [];
var tempData = [];

function MainScreen({ navigation }) {
  const {d, setData} = React.useContext(DataContext);
  const {v, setVisibility} = React.useContext(VisibilityContext);
  

  const fetchData = async () => {
    try {
      const response = await fetch('http://10.0.0.169:3000');
        setData(await response.json());
    } catch (error) {
      console.log('Failed to fetch', error);
    }
  }

  useEffect(() => {
    fetchData();
    // console.log(test)
  }, []);

  var test = scaleData(sortData(d));

  outPath = renderPath(test);
  outPoints = renderPoints(test);
  // useEffect(() => {
  //   fetch('http://10.0.0.169:3000',{
  //     method: 'GET'
  //   }).then(response => response.json())
  //   .then(data => setData(data))
  //   .catch(error => console.error(error))
  // }, []);

  
  var axis = renderAxis();
  var ticks = renderTicks();

  setVisibility(visible)
  console.log(v)
  return (
    <>
      <View style={styles.container}>
          <Canvas style={{width: cDim.w+offset+50, height: cDim.h+offset+paddingY}}>
            <Rect x={offset+paddingX} y={paddingY} width={drawDim.w} height={drawDim.h} color="#E1E1E1"></Rect>
            
            {axis}
            {ticks}
            {outPath}
            {outPoints}
            {/* <Path path={p} style="stroke" strokeWidth={4} color="#3EB489"/>
            <Points points={pts} mode="points" color="red" style="fill" strokeWidth={6}></Points> */}
          </Canvas>
          <Button onPress={async ()=> {
              await fetch('http://10.0.0.169:3000',{
                method: 'GET'
              }).then(response => response.json())
              .then(data => setData(data))
              .catch(error => console.error(error));setVisibility(visible)
              } } 
            title="Refresh Data"></Button>
          {/* <Button onPress={}></Button> */}
      </View>
    </>
  )
}

var dispDim = {w: Dimensions.get("window").width, h: Dimensions.get("window").height};
const cDim = {w:350, h:400};
const offset = 30;
const drawDim = {w: cDim.w-offset, h: cDim.h-offset}

var definedArea = {w:500, h:500};
var scaleX = drawDim.w/definedArea.w;
var scaleY = drawDim.h/definedArea.h;

const scaleData = (dataArray) => {
  // console.log(dataArray)
  var temp = dataArray;
  for (var i=0;i<temp.length;i++) {
    for (var j=0;j<temp[i].length;j++) {
      temp[i][j].x = temp[i][j].x*scaleX;
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

  return (<Path path = {p} style="stroke" strokeWidth={2} color="black"></Path>)
}

const renderTicks = () => {
  var ticks = [];
  const p = Skia.Path.Make();
  const fsize = 12;
  const fontFamily = Platform.select({ default: "serif" });

  const fontStyle = {
    fontFamily,
    fontSize: fsize,
    fontStyle: "normal",
    fontWeight: "normal",
  };
  const font = matchFont(fontStyle);

  const xTicks = 5;
  const yTicks = 5;

  // const xTicks = parseInt(definedArea.w/100);
  // const yTicks = parseInt(definedArea.y/100);

  const xDimInc = (drawDim.w/xTicks);
  const xValueInc = definedArea.w/xTicks;
  var diff = 0;

  for (var i=0;i<=xTicks;i++) {
    diff = (xValueInc*i+"").length;
    
    // console.log((i*xDimInc)+offset+"")
    // console.log(diff);

    p.moveTo((i*xDimInc)+offset+paddingX, cDim.h-offset+paddingY);
    p.lineTo((i*xDimInc)+offset+paddingX, cDim.h-offset+8+paddingY);

    ticks.push(<Text x={(i*xDimInc)+offset+paddingX-(diff*3.3)} y={drawDim.h+20+paddingY} text={xValueInc*i+""} font = {font}></Text>)
  }

  const yDimInc = (drawDim.h/yTicks);
  const yValueInc = definedArea.h/yTicks;
  var counter = 0;
  for (var i=yTicks;i>=0;i--) {
    diff = (yValueInc*counter+"").length;

    p.moveTo(offset+paddingX, i*yDimInc+paddingY);
    p.lineTo(offset+paddingX-8, i*yDimInc+paddingY);

    ticks.push(<Text x={offset+paddingX-(diff*7)-11} y={(i*yDimInc+paddingY+4)} text={yValueInc*counter+""} font = {font}></Text>)
    counter = counter + 1
  }

  ticks.push(<Path path = {p} style="stroke" strokeWidth={1} color="black"></Path>)
  
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
        <Points key={ukey} points={p} mode="points" color="red" style="fill" strokeWidth={6}></Points>
      )
    }
    
  }
  return out;
}

const Drawer = createDrawerNavigator();



function ListItems(props) {
  const {v, setVisibility} = React.useContext(VisibilityContext);
  const {d, setData} = React.useContext(DataContext)

  const renderDrawPathItems = (vis) => {
    var out = [];
    for (var i=0; i<vis.length; i++) {
      const tar = vis[i].target+"";
      out.push(<DrawerItem key={tar} label={tar} onPress={()=>{togglePath(tar); fetch('http://10.0.0.169:3000',{
        method: 'GET'
      }).then(response => response.json())
      .then(data => setData(data))
      .catch(error => console.error(error))}}></DrawerItem>)
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


const DataContext = React.createContext([]);
const VisibilityContext = React.createContext([]);
const RefreshContext = React.createContext([]);

export default function App() {
  const [d, setData] = React.useState([]);
  const [v, setVisibility] = React.useState([]);
  const [, forceUpdate] = React.useReducer(r => r+1, 0);
  
  // var arr = sortData(d);
  // console.log(arr)
  
  return (
    <RefreshContext.Provider value={{ forceUpdate }}>
      <DataContext.Provider value={{ d, setData }}>
        <VisibilityContext.Provider value={{v, setVisibility}}>
          <NavigationContainer>
            <PathList></PathList>
          </NavigationContainer>
        </VisibilityContext.Provider>
      </DataContext.Provider>
    </RefreshContext.Provider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 50,
    paddingHorizontal: 20,
    paddingBottom: 100,
    backgroundColor: '#fff',
    // alignItems: 'center',
    justifyContent: 'center',
    // height: 500
  },
});