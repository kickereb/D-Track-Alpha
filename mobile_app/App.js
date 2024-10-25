// "use client";
import {Canvas, Path, Skia, vec, Points, Rect } from "@shopify/react-native-skia";
import React, {useState, useEffect } from "react";
import { StyleSheet, View, Text, Dimensions } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createDrawerNavigator, DrawerContentScrollView, DrawerItemList, DrawerItem } from "@react-navigation/drawer";

const sortData = (dataArr) => {
  var result = [];
  var seen = [];
  for (var i=0;i<dataArr.length;i++) {
    if (!seen.some(x => x === dataArr[i].target)) {
      var temp = [{x: dataArr[i].x, y: dataArr[i].y, target: dataArr[i].target}];
      seen.push(dataArr[i].target);
      result.push(temp);
    } else {
      result[seen.indexOf(dataArr[i].target)].push({x: dataArr[i].x, y: dataArr[i].y, target: dataArr[i].target});
    }
  }
  return result;
}

const getData = () => {

  const [d, setData] = useState('');

  useEffect(() => {
    fetch('http://10.0.0.169:3000',{
      method: 'GET'
    }).then(response => response.json())
    .then(data => setData(data))
    .catch(error => console.error(error))
  }, []);
  return d;
}

const renderPath = () => {
  
}

const renderPoints = () => {

}

function MainScreen() {
  var outPath = [];
  var outPoints = [];
  
  var allowedColors = ["blue", "green", "yellow", "black", "white", "purple", "cyan", "magenta", "lime", "orange"];

  const d = getData();

  var test = scaleData(sortData(d));

  for (let i=0;i<test.length;i++) {
    const p = drawPath(test[i]);
    const pts = drawPoints(test[i]);

    outPath.push(
      <Path path={p} style="stroke" strokeWidth={4} color={allowedColors[i%allowedColors.length]}/>
    );
    outPoints.push(
      <Points points={pts} mode="points" color="red" style="fill" strokeWidth={6}></Points>
    )
  }

  return (
    <>
      <View style={styles.container}>
          <Canvas style={{width: cDim.w, height: cDim.h}}>
            <Rect x={0} y={0} width={cDim.w} height={cDim.h} color="#E1E1E1"></Rect>
            {outPath}
            {outPoints}
            {/* <Path path={p} style="stroke" strokeWidth={4} color="#3EB489"/>
            <Points points={pts} mode="points" color="red" style="fill" strokeWidth={6}></Points> */}
          </Canvas>
      </View>
    </>
  )
}

var dispDim = {w: Dimensions.get("window").width, h: Dimensions.get("window").height};
const cDim = {w:350, h:500};

var definedArea = {w:500, h:500};
var scaleX = cDim.w/definedArea.w;
var scaleY = cDim.h/definedArea.h;

const scaleData = (dArr) => {
  var temp = dArr;
  for (var i=0;i<temp.length;i++) {
    for (var j=0;j<temp.length;j++) {
      temp[i][j].x = temp[i][j].x*scaleX;
      temp[i][j].y = temp[i][j].y*scaleY;
      // Il include it here after testing
      // dArr[i][j].y = cDim.h - dArr[i][j].y
    }
  }
  return temp;
}

function ListItems(props) {
  return (
    <DrawerContentScrollView {...props}>
      <DrawerItemList {...props} />
    </DrawerContentScrollView>
    
  )
}

function PathList({tracked}) {
  return (
    <Drawer.Navigator
      drawerContent={(props) => <ListItems {...props} />}
      
    >
      <Drawer.Screen name="MainScreen" component={MainScreen} options ={{ drawerItemStyle: { display: 'none'}}} />
    </Drawer.Navigator>
  )
}

const drawPath = (dArr) => {
  const path = Skia.Path.Make();
  path.moveTo(parseFloat(dArr[0].x),cDim.h-parseFloat(dArr[0].y))
  for (var i=1;i<dArr.length;i++) {
    path.lineTo(parseFloat(dArr[i].x), cDim.h-parseFloat(dArr[i].y));
  }
  return path;
}

const drawPoints = (dArr) => {
  var points = [];
  for (var i=0;i<dArr.length;i++) {
    points.push(vec(parseFloat(dArr[i].x),cDim.h-parseFloat(dArr[i].y)))
  }
  return points;
}


const Drawer = createDrawerNavigator();

export default function App() {
  var bList = [];
  
  // var arr = sortData(d);
  // console.log(arr)
  
  return (
    <NavigationContainer>
      <PathList tracked = {bList}></PathList>
    </NavigationContainer>
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