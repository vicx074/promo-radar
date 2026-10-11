import {afterEach,describe,expect,it,vi} from "vitest";
import {ApiError, apiRequest} from "./api";

afterEach(()=>{vi.unstubAllGlobals();});

describe("API administrativa",()=>{
  it("envia chave somente em header e mantém rota na mesma origem",async()=>{
    const mock=vi.fn(async()=>new Response(JSON.stringify({status:"DISCONNECTED"}),{
      status:200,headers:{"Content-Type":"application/json"},
    }));
    vi.stubGlobal("fetch",mock);
    const result=await apiRequest<{status:string}>("chave-ficticia","/api/v1/affiliates/mercado-livre/status");
    expect(result.status).toBe("DISCONNECTED");
    const [path,init]=mock.mock.calls[0] as unknown as [string,RequestInit];
    expect(path).toBe("/api/v1/affiliates/mercado-livre/status");
    expect(init.headers).toMatchObject({"x-admin-key":"chave-ficticia"});
    expect(init.credentials).toBe("omit");
    expect(path).not.toContain("chave-ficticia");
  });
  it("rejeita chamadas arbitrárias que poderiam expor a chave",async()=>{
    const mock=vi.fn();
    vi.stubGlobal("fetch",mock);
    await expect(apiRequest("secret","https://evil.example/test")).rejects.toThrow("Rota inválida");
    await expect(apiRequest("secret","//evil.example/api/v1/test")).rejects.toThrow("Rota inválida");
    expect(mock).not.toHaveBeenCalled();
  });
  it("informa erros de validação e autenticação",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({detail:"Chave administrativa inválida"}),{
      status:401,headers:{"Content-Type":"application/json"},
    })));
    await expect(apiRequest("fake","/api/v1/offers")).rejects.toEqual(new ApiError("Chave administrativa inválida",401));
  });
  it("envia JSON de criação somente por POST",async()=>{
    const mock=vi.fn(async()=>new Response(JSON.stringify({selected:[]}),{
      status:200,headers:{"Content-Type":"application/json"},
    }));
    vi.stubGlobal("fetch",mock);
    await apiRequest("secret","/api/v1/discovery/select",{method:"POST",body:{search_id:"fake",source_item_ids:["MLB123"]}});
    const [,init]=mock.mock.calls[0] as unknown as [string,RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toMatchObject({source_item_ids:["MLB123"]});
    expect(init.headers).toMatchObject({"Content-Type":"application/json"});
  });
});
