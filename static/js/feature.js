
function displayDate(){
    document.getElementById("demo1").innerHTML=Date();
}
function displayTime(){
    document.getElementById("time").innerHTML=new Date().toLocaleTimeString();
}

/*
function displayWeather(){
    document.getElementById("weather").innerHTML= new Date();
    var fso=new ActiveXObject(Scripting.FileSystemObject);
    var f=fso.opentextfile('E:/awesome-python3-webapp/www/newfeature/theWeather.txt',1, true);  
    while (!f.AtEndOfStream){
        f.Readline();
    } 
}
*/

function displayWeather(){
    var fso, ts, s="" ;
    var ForReading = 1;

    fso = new ActiveXObject("Scripting.FileSystemObject");
    ts = fso.OpenTextFile('E:/awesome-python3-webapp/www/newfeature/theWeather.txt', ForReading);
    while (!ts.AtEndOfStream){
        s=ts.Readline();
    } 
    document.getElementById("weather").innerHTML=s;
}