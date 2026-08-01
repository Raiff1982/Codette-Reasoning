using Microsoft.AspNetCore.Mvc.RazorPages;
using System.Threading.Tasks;

public class IndexModel : PageModel
{
    private readonly MyBot _bot;

    public IndexModel(MyBot bot)
    {
        _bot = bot;
    }

    [BindProperty]
    public string UserInput { get; set; }
    public string Response { get; set; }

    public async Task OnPostAsync()
    {
        if (!string.IsNullOrEmpty(UserInput))
        {
            Response = await _bot.GenerateResponse(UserInput, "webUser");
        }
    }
}