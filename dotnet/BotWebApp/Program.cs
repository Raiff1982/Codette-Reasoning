using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

class Program
{
    private static IConfiguration Configuration;
    private static ILogger<Program> Logger;

    public static async Task Main(string[] args)
    {
        // Load environment variables from .env file
        var builder = new ConfigurationBuilder()
            .SetBasePath(Directory.GetCurrentDirectory())
            .AddJsonFile("appsettings.json", optional: true, reloadOnChange: true)
            .AddEnvironmentVariables();
        Configuration = builder.Build();

        // Configure logging
        using var loggerFactory = LoggerFactory.Create(loggingBuilder =>
        {
            loggingBuilder.AddConsole();
            loggingBuilder.AddConfiguration(Configuration.GetSection("Logging"));
        });
        Logger = loggerFactory.CreateLogger<Program>();

        // Setup dependency injection
        var serviceProvider = new ServiceCollection()
            .AddSingleton(Configuration)
            .AddSingleton(Logger)
            .AddSingleton<SentimentAnalysis>()
            .AddSingleton<MyBot>()
            .AddHttpClient()
            .BuildServiceProvider();

        // Example usage of MyBot class
        var bot = serviceProvider.GetService<MyBot>();
        await bot.GenerateResponse("Hello, how are you?", "user123");

        // Start the web host
        CreateHostBuilder(args).Build().Run();
    }

    public static IHostBuilder CreateHostBuilder(string[] args) =>
        Host.CreateDefaultBuilder(args)
            .ConfigureWebHostDefaults(webBuilder =>
            {
                webBuilder.UseStartup<Startup>();
            });
}