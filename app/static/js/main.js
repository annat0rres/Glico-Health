document.addEventListener("DOMContentLoaded", () => {
    const camadaLuzes = document.querySelector(".luzesGradiente");

    if (camadaLuzes) {
        const quantidadeLuzes = 34;
        const sortear = (minimo, maximo) => Math.random() * (maximo - minimo) + minimo;

        for (let i = 0; i < quantidadeLuzes; i += 1) {
            const luz = document.createElement("span");
            const duracao = sortear(6, 16);
            const luzDeBorda = i >= 20;
            const luzAmarela = i >= 30;
            const tamanho = luzDeBorda
                ? sortear(14, 26)
                : i < 14
                    ? sortear(12, 32)
                    : sortear(32, 60);
            let inicioX;
            let inicioY;
            let destinoX;
            let destinoY;

            if (luzDeBorda) {
                switch (i % 4) {
                    case 0:
                        inicioX = sortear(0, 70);
                        inicioY = sortear(-8, 8);
                        destinoX = sortear(0, 70);
                        destinoY = sortear(65, 80);
                        break;
                    case 1:
                        inicioX = sortear(55, 78);
                        inicioY = sortear(0, 75);
                        destinoX = sortear(0, 15);
                        destinoY = sortear(0, 75);
                        break;
                    case 2:
                        inicioX = sortear(0, 70);
                        inicioY = sortear(65, 80);
                        destinoX = sortear(0, 70);
                        destinoY = sortear(-8, 8);
                        break;
                    default:
                        inicioX = sortear(0, 15);
                        inicioY = sortear(0, 75);
                        destinoX = sortear(55, 78);
                        destinoY = sortear(0, 75);
                        break;
                }
            } else {
                inicioX = sortear(0, 70);
                inicioY = sortear(0, 75);
                destinoX = inicioX < 35 ? sortear(55, 75) : sortear(0, 20);
                destinoY = inicioY < 37.5 ? sortear(55, 80) : sortear(0, 20);
            }

            luz.classList.add("manchaLuz");
            if (luzDeBorda) {
                luz.classList.add("manchaLuz--borda");
            }
            let classeCor = Math.random() < 0.5 ? "manchaLuz--rosa" : "manchaLuz--lilas";

            if (luzAmarela) {
                classeCor = "manchaLuz--amarela";
            } else if (luzDeBorda && i % 3 === 0) {
                classeCor = "manchaLuz--clara";
            }

            luz.classList.add(classeCor);
            luz.style.setProperty("--tamanho", `${tamanho.toFixed(1)}vw`);
            luz.style.setProperty("--inicio-x", `${inicioX.toFixed(1)}vw`);
            luz.style.setProperty("--inicio-y", `${inicioY.toFixed(1)}vh`);
            luz.style.setProperty("--destino-x", `${destinoX.toFixed(1)}vw`);
            luz.style.setProperty("--destino-y", `${destinoY.toFixed(1)}vh`);
            luz.style.setProperty("--duracao", `${duracao.toFixed(1)}s`);
            luz.style.setProperty("--atraso", `${(-Math.random() * duracao).toFixed(1)}s`);
            camadaLuzes.appendChild(luz);
        }
    }

    const botaoAvancar = document.querySelector("#avance");

    if (botaoAvancar) {
        botaoAvancar.addEventListener("click", () => {
            window.location.href = "/cadastro"; 
        });
    }
});