(() => {
    "use strict";
    const c = window.workspaceDetailConfig || {};
    const grid = document.getElementById("workspaceDashboardGrid");
    const search = document.getElementById("dashboardSearchInput");
    const type = document.getElementById("dashboardTypeFilter");
    const sort = document.getElementById("dashboardSortSelect");
    const favOnly = document.getElementById("dashboardFavoritesOnly");
    const empty = document.getElementById("workspaceDashboardEmptyState");
    const alertBox = document.getElementById("workspaceDetailAlert");
    const modal = document.getElementById("renameDashboardModal");
    const form = document.getElementById("renameDashboardForm");
    const idInput = document.getElementById("renameDashboardId");
    const nameInput = document.getElementById("renameDashboardName");
    const descInput = document.getElementById("renameDashboardDescription");
    const saveBtn = document.getElementById("saveRenameDashboardButton");

    const cards = () => grid ? Array.from(grid.querySelectorAll(".wd-card")) : [];
    const show = (m,t="success") => { if(!alertBox) return; alertBox.textContent=m; alertBox.className=`wd-alert ${t}`; alertBox.style.display="block"; setTimeout(()=>alertBox.style.display="none",3000); };
    const req = async (url, options={}) => { const r=await fetch(url,{...options,headers:{"Content-Type":"application/json",...(options.headers||{})}}); const j=await r.json(); if(!r.ok||!j.success) throw new Error(j.message||"Request failed"); return j; };

    function applyFilters(){
        const q=(search?.value||"").trim().toLowerCase();
        const selected=type?.value||"all";
        const only=Boolean(favOnly?.checked);
        let visible=0;
        cards().forEach(card=>{
            const okName=!q||(card.dataset.dashboardName||"").includes(q);
            const okType=selected==="all"||card.dataset.dashboardType===selected;
            const okFav=!only||card.dataset.dashboardFavorite==="1";
            const ok=okName&&okType&&okFav;
            card.style.display=ok?"":"none";
            if(ok) visible++;
        });
        if(empty) empty.style.display=visible?"none":"block";
    }

    function sortCards(){
        if(!grid) return;
        const mode=sort?.value||"updated";
        const arr=cards();
        arr.sort((a,b)=>{
            if(mode==="name") return (a.dataset.dashboardName||"").localeCompare(b.dataset.dashboardName||"");
            if(mode==="favorites") return Number(b.dataset.dashboardFavorite||0)-Number(a.dataset.dashboardFavorite||0);
            return String(b.dataset.dashboardUpdated||"").localeCompare(String(a.dataset.dashboardUpdated||""));
        });
        arr.forEach(x=>grid.appendChild(x));
        applyFilters();
    }

    function openDashboard(t,f){
        if(!f){ show("Saved dashboard has no dataset file.","error"); return; }
        let url=c.executiveBaseUrl+encodeURIComponent(f);
        if(t==="forecast") url=c.forecastBaseUrl+encodeURIComponent(f);
        else if(t==="analytics") url=c.analyticsBaseUrl+encodeURIComponent(f);
        else if(t==="preview") url=c.previewBaseUrl+encodeURIComponent(f);
        location.href=url;
    }

    function openRename(id,name,description){ idInput.value=id||""; nameInput.value=name||""; descInput.value=description||""; modal?.classList.add("open"); modal?.setAttribute("aria-hidden","false"); setTimeout(()=>nameInput.focus(),50); }
    function closeRename(){ modal?.classList.remove("open"); modal?.setAttribute("aria-hidden","true"); form?.reset(); idInput.value=""; }

    form?.addEventListener("submit", async e=>{
        e.preventDefault();
        const id=idInput.value, name=nameInput.value.trim(), description=descInput.value.trim();
        if(!id||!name){ show("Dashboard name is required.","error"); return; }
        saveBtn.disabled=true; saveBtn.textContent="Saving...";
        try{ await req(`${c.dashboardBaseUrl}/${id}`,{method:"PUT",body:JSON.stringify({name,description})}); location.reload(); }
        catch(err){ show(err.message,"error"); }
        finally{ saveBtn.disabled=false; saveBtn.textContent="Save Changes"; }
    });

    grid?.addEventListener("click", async e=>{
        const b=e.target.closest("[data-action]"); if(!b) return;
        const action=b.dataset.action, id=b.dataset.dashboardId;
        const card=b.closest(".wd-card");
        const name=b.dataset.dashboardName||card?.querySelector("h2")?.textContent?.trim()||"Dashboard";
        try{
            if(action==="open") openDashboard(b.dataset.dashboardType,b.dataset.filename);
            else if(action==="rename") openRename(id,b.dataset.dashboardName,b.dataset.dashboardDescription);
            else if(action==="favorite"){
                const result=await req(`${c.dashboardBaseUrl}/${id}/favorite`,{method:"POST",body:"{}"});
                const isFav=Boolean(result.dashboard?.is_favorite); b.classList.toggle("active",isFav); card.dataset.dashboardFavorite=isFav?"1":"0"; sortCards();
            }
            else if(action==="duplicate"){
                const copy=prompt("Name for duplicated dashboard:",`${name} Copy`); if(copy===null) return; if(!copy.trim()){show("Duplicate dashboard name is required.","error");return;}
                await req(`${c.dashboardBaseUrl}/${id}/duplicate`,{method:"POST",body:JSON.stringify({workspace_id:c.workspaceId,name:copy.trim()})}); location.reload();
            }
            else if(action==="delete"){
                if(!confirm(`Delete "${name}" permanently?`)) return;
                await req(`${c.dashboardBaseUrl}/${id}`,{method:"DELETE"}); card.remove(); applyFilters(); show("Dashboard deleted successfully.");
            }
        }catch(err){ show(err.message,"error"); }
    });

    document.querySelectorAll("[data-open-dashboard]").forEach(b=>b.addEventListener("click",()=>openDashboard(b.dataset.dashboardType,b.dataset.filename)));
    document.querySelectorAll("[data-close-rename-modal]").forEach(b=>b.addEventListener("click",closeRename));
    modal?.querySelector(".wd-backdrop")?.addEventListener("click",closeRename);
    search?.addEventListener("input",applyFilters);
    type?.addEventListener("change",applyFilters);
    favOnly?.addEventListener("change",applyFilters);
    sort?.addEventListener("change",sortCards);
    document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&modal?.classList.contains("open")) closeRename(); });
    sortCards();
})();
