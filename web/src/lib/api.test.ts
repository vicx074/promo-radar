import {afterEach,describe,expect,it,vi} from "vitest";
import {ApiError, apiRequest, loginOwner, logoutOwner, restoreSession} from "./api";

afterEach(()=>vi.unstubAllGlobals());

describe("sessão do operador privado",()=>{
  it("usa sessão HttpOnly e CSRF em memória, sem x-admin-key",async()=>{
    const calls:Array<[string,RequestInit]>=[];
    vi.stubGlobal("fetch",vi.fn(async(path:string,options:RequestInit)=>{
      calls.push([path,options]);
      if(path==="/api/v1/auth/login")return new Response(JSON.stringify({
        authenticated:true,csrf_token:"fake-csrf",expires_at:123456,
      }),{status:200});
      if(path==="/api/v1/auth/logout")return new Response(JSON.stringify({authenticated:false}),{status:200});
      return new Response(JSON.stringify({selected:[]}),{status:200});
    }));
    await loginOwner("senha-somente-teste");
    await apiRequest("/api/v1/discovery/select",{method:"POST",body:{search_id:"fake",source_item_ids:["MLB123"]}});
    expect(calls[0][0]).toBe("/api/v1/auth/login");
    expect(calls[0][1].credentials).toBe("same-origin");
    expect(calls[1][1].headers).toMatchObject({"x-csrf-token":"fake-csrf"});
    expect(JSON.stringify(calls[1])).not.toContain("senha-somente-teste");
    expect(JSON.stringify(calls)).not.toContain("x-admin-key");
    await logoutOwner();
    expect(calls[2][1].headers).toMatchObject({"x-csrf-token":"fake-csrf"});
  });
  it("restaura csrf de uma sessão persistida no cookie",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({
      authenticated:true,csrf_token:"csrf-recuperado",expires_at:123,
    }),{status:200})));
    const restored=await restoreSession();
    expect(restored.csrf_token).toBe("csrf-recuperado");
  });
  it("rejeita URLs externas sem enviar requisições",async()=>{
    const mock=vi.fn();
    vi.stubGlobal("fetch",mock);
    await expect(apiRequest("https://evil.example")).rejects.toThrow("Rota inválida");
    await expect(apiRequest("//evil.example/api/v1/offers")).rejects.toThrow("Rota inválida");
    expect(mock).not.toHaveBeenCalled();
  });
  it("expõe erros de autenticação sem vazar senha",async()=>{
    vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({detail:"Senha incorreta"}),{status:401})));
    await expect(loginOwner("senha-errada")).rejects.toEqual(new ApiError("Senha incorreta",401));
  });
});
