/* Cover framing for the permanent Studio. User controls size, pan and saved framing. */
(function(){
"use strict";
const $=id=>document.getElementById(id),box=$("coverBox"),pic=$("coverPreview");
if(!box||!pic)return;
let crop={x:50,y:50,zoom:1},pointer=null;
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
const panel=document.createElement("section");
panel.id="zt-cover-adjust";
panel.setAttribute("aria-label","Regola la copertina");
panel.innerHTML='<div class="zt-cover-title">Regola la copertina <span>Trascina la foto con il mouse per centrarla</span></div><div class="zt-cover-settings"><label>Ingrandisci o riduci <output id="ztCoverZoomOut">100%</output><input id="ztCoverZoom" type="range" min="100" max="300" step="5" value="100"></label><label>Destra / sinistra <output id="ztCoverXOut">50%</output><input id="ztCoverX" type="range" min="0" max="100" value="50"></label><label>Su / giù <output id="ztCoverYOut">50%</output><input id="ztCoverY" type="range" min="0" max="100" value="50"></label></div><div class="zt-cover-actions"><button type="button" id="ztCoverMinus">− Riduci</button><button type="button" id="ztCoverPlus">+ Ingrandisci</button><button type="button" id="ztCoverCenter">Centra</button></div>';
box.insertAdjacentElement("afterend",panel);
const st=document.createElement("style");st.textContent='#zt-cover-adjust{background:#f8f9fb;border:1px solid #e3e5ea;border-radius:10px;padding:16px 20px;margin:-15px 0 27px}#zt-cover-adjust .zt-cover-title{font-size:14px;font-weight:850;color:#222}#zt-cover-adjust .zt-cover-title span{display:block;font-size:12px;font-weight:400;color:#68717d;margin-top:4px}#zt-cover-adjust .zt-cover-settings{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;margin:15px 0}#zt-cover-adjust label{font-size:12px;font-weight:750;color:#424b58;min-width:0}#zt-cover-adjust output{color:#d51232;margin-left:5px}#zt-cover-adjust input[type=range]{display:block;width:100%;margin-top:9px;accent-color:#d51232}#zt-cover-adjust .zt-cover-actions{display:flex;gap:8px;flex-wrap:wrap}#zt-cover-adjust button{border:1px solid #d7dce5;background:#fff;color:#272d36;border-radius:6px;padding:7px 12px;font-weight:750;font-size:12px}#coverBox.hascover{touch-action:none;cursor:grab}#coverBox.hascover:active{cursor:grabbing}#coverBox .coverimg{max-width:none;user-select:none;pointer-events:none;will-change:transform}#coverBox .coverchange{z-index:5}@media(max-width:680px){#zt-cover-adjust .zt-cover-settings{grid-template-columns:1fr}}';
document.head.append(st);
function get(){return {x:crop.x,y:crop.y,zoom:crop.zoom}}
function set(v){crop={x:clamp(Number(v?.x??50),0,100),y:clamp(Number(v?.y??50),0,100),zoom:clamp(Number(v?.zoom??1),1,3)};render();}
function render(){pic.style.setProperty("transform","scale("+crop.zoom+")","important");pic.style.setProperty("transform-origin",crop.x+"% "+crop.y+"%","important");pic.style.setProperty("object-position",crop.x+"% "+crop.y+"%","important");for(let p of ["X","Y","Zoom"]){let val=p==="X"?crop.x:p==="Y"?crop.y:crop.zoom*100;const input=$("ztCover"+p);input.value=String(val);$("ztCover"+p+"Out").textContent=Math.round(val)+"%"}panel.hidden=!pic.getAttribute("src");}
function change(){crop.x=Number($("ztCoverX").value);crop.y=Number($("ztCoverY").value);crop.zoom=Number($("ztCoverZoom").value)/100;render();window.ZTStudio?.saveDraft?.(true)}
["X","Y","Zoom"].forEach(p=>$("ztCover"+p).addEventListener("input",change));
$("ztCoverPlus").onclick=()=>{crop.zoom=clamp(crop.zoom+.10,1,3);render();window.ZTStudio?.saveDraft?.(true)};
$("ztCoverMinus").onclick=()=>{crop.zoom=clamp(crop.zoom-.10,1,3);render();window.ZTStudio?.saveDraft?.(true)};
$("ztCoverCenter").onclick=()=>{set({x:50,y:50,zoom:1});window.ZTStudio?.saveDraft?.(true)};
box.addEventListener("pointerdown",e=>{if(!box.classList.contains("hascover")||e.target.closest("button"))return;pointer={px:e.clientX,py:e.clientY,x:crop.x,y:crop.y};box.setPointerCapture?.(e.pointerId)});
box.addEventListener("pointermove",e=>{if(!pointer)return;const dx=e.clientX-pointer.px,dy=e.clientY-pointer.py;if(Math.abs(dx)+Math.abs(dy)<3)return;if(crop.zoom<1.1)crop.zoom=1.3;crop.x=clamp(pointer.x-dx/Math.max(1,box.clientWidth)*100/(crop.zoom-1),0,100);crop.y=clamp(pointer.y-dy/Math.max(1,box.clientHeight)*100/(crop.zoom-1),0,100);render()});
box.addEventListener("pointerup",()=>{if(pointer){pointer=null;window.ZTStudio?.saveDraft?.(true)}});
box.addEventListener("pointercancel",()=>pointer=null);
function exportCover(){
 if(!pic.complete||!pic.naturalWidth||!pic.naturalHeight)return null;
 const iw=pic.naturalWidth,ih=pic.naturalHeight,ratio=16/9;
 let sw=Math.min(iw,ih*ratio),sh=sw/ratio;
 let sx=(iw-sw)*crop.x/100,sy=(ih-sh)*crop.y/100;
 sx+=(sw-sw/crop.zoom)*crop.x/100;sy+=(sh-sh/crop.zoom)*crop.y/100;
 sw/=crop.zoom;sh/=crop.zoom;
 const canvas=document.createElement("canvas");canvas.width=1200;canvas.height=675;
 const ctx=canvas.getContext("2d");
 ctx.drawImage(pic,sx,sy,sw,sh,0,0,1200,675);
 return canvas.toDataURL("image/jpeg",.86);
}
window.ZTStudioCover={get,set,render,export:exportCover};
render();
})();
